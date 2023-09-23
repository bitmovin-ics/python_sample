import time

from bitmovin_api_sdk import BitmovinApi
from bitmovin_api_sdk import S3Input, S3Output
from bitmovin_api_sdk import Encoding, CloudRegion
from bitmovin_api_sdk import EncodingOutput, AclEntry, AclPermission
from bitmovin_api_sdk import Stream, StreamInput, MuxingStream, StreamMode
from bitmovin_api_sdk import DolbyAtmosAudioConfiguration, DolbyAtmosLoudnessControl, DolbyAtmosMeteringMode
from bitmovin_api_sdk import DolbyAtmosDialogueIntelligence, DolbyAtmosIngestInputStream, DolbyAtmosInputFormat
from bitmovin_api_sdk import CodecConfigType
from bitmovin_api_sdk import Fmp4Muxing
from bitmovin_api_sdk import DashManifest, Period, AudioAdaptationSet
from bitmovin_api_sdk import DashFmp4Representation, DashRepresentationType, DashRepresentationTypeMode
from bitmovin_api_sdk import HlsManifest, HlsVersion, StreamInfo, AudioMediaInfo
from bitmovin_api_sdk import MessageType, StartEncodingRequest
from bitmovin_api_sdk import Status

TEST_ITEM = "audio-only-dolbyatmos-damf-hls-dash-fmp4"

API_KEY = '<INSERT YOUR API KEY>'
ORG_ID = '<INSERT YOUR ORG ID>'

S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

S3_OUTPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_OUTPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_OUTPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

# from https://opencontent.netflix.com/
DOLBY_ATMOS_DAMF_PATH = 'netflix-opencontent/SolLevante/atmos-damf/sollevante_lp_v01_DAMF_Nearfield_48k_24b_24/sollevante_lp_v01_DAMF_Nearfield_48k_24b_24.atmos'

OUTPUT_BASE_PATH = 'output/{}/'.format(TEST_ITEM)

bitmovin_api = BitmovinApi(api_key=API_KEY, tenant_org_id=ORG_ID)

encoding_profiles_atmos = [
    dict(bitrate=448000, rate=48_000)
]


def main():
    # === Input and Output definition ===
    s3_input = bitmovin_api.encoding.inputs.s3.create(
        s3_input=S3Input(
            access_key=S3_INPUT_ACCESS_KEY,
            secret_key=S3_INPUT_SECRET_KEY,
            bucket_name=S3_INPUT_BUCKET_NAME,
            name='Test S3 Input'))
    s3_output = bitmovin_api.encoding.outputs.s3.create(
        s3_output=S3Output(
            access_key=S3_OUTPUT_ACCESS_KEY,
            secret_key=S3_OUTPUT_SECRET_KEY,
            bucket_name=S3_OUTPUT_BUCKET_NAME,
            name='Test S3 Output'))

    # === Encoding definition ===
    encoding = bitmovin_api.encoding.encodings.create(
        encoding=Encoding(
            name='{}'.format(TEST_ITEM),
            cloud_region=CloudRegion.AWS_AP_NORTHEAST_1,
            encoder_version='STABLE'))

    # === Input Stream definition (only audio stream) ===
    audio_ingest_input_stream = bitmovin_api.encoding.encodings.input_streams.dolby_atmos.create(
        encoding_id=encoding.id,
        dolby_atmos_ingest_input_stream=DolbyAtmosIngestInputStream(
            input_id=s3_input.id,
            input_path=DOLBY_ATMOS_DAMF_PATH,
            input_format=DolbyAtmosInputFormat.DAMF))
    audio_input_stream = StreamInput(input_stream_id=audio_ingest_input_stream.id)

    # === Audio Codec Configuration definition ===
    audio_encoding_configs = []
    for idx, _ in enumerate(encoding_profiles_atmos):
        profile_atmos = encoding_profiles_atmos[idx]
        encoding_config = dict(profile_atmos=profile_atmos)
        encoding_config['atmos_codec'] = bitmovin_api.encoding.configurations.audio.dolby_atmos.create(
            dolby_atmos_audio_configuration=DolbyAtmosAudioConfiguration(
                bitrate=profile_atmos.get("bitrate"),
                rate=profile_atmos.get("rate"),
                loudness_control=DolbyAtmosLoudnessControl(
                    metering_mode=DolbyAtmosMeteringMode.ITU_R_BS_1770_4,
                    dialogue_intelligence=DolbyAtmosDialogueIntelligence.ENABLED,
                    speech_threshold=15
                )
            ))
        audio_encoding_configs.append(encoding_config)

    # === Audio Stream definition ===
    for encoding_config in audio_encoding_configs:
        encoding_profile = encoding_config.get("profile_atmos")
        audio_stream = Stream(
            codec_config_id=encoding_config.get("atmos_codec").id,
            input_streams=[audio_input_stream],
            name='Stream Atmos {}bps'.format(encoding_profile.get('bitrate')),
            mode=StreamMode.STANDARD
        )
        encoding_config['atmos_stream'] = bitmovin_api.encoding.encodings.streams.create(
            encoding_id=encoding.id, stream=audio_stream)

    # === Fmp4 Muxings ===
    for encoding_config in audio_encoding_configs:
        encoding_profile = encoding_config.get("profile_atmos")
        audio_muxing_stream = MuxingStream(stream_id=encoding_config['atmos_stream'].id)
        audio_muxing_output = EncodingOutput(output_id=s3_output.id,
                                             output_path=OUTPUT_BASE_PATH + "audio/{}".format(encoding_profile.get('bitrate')),
                                             acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])
        bitmovin_api.encoding.encodings.muxings.fmp4.create(
            encoding_id=encoding.id,
            fmp4_muxing=Fmp4Muxing(
                segment_length=6,
                segment_naming='seg_%number%.m4s',
                init_segment_name='init.mp4',
                streams=[audio_muxing_stream],
                outputs=[audio_muxing_output],
                name="Audio FMP4 Muxing {}bps".format(encoding_profile.get('bitrate'))))

    # === Start Encoding settings together with DASh & HLS Manifest definition ===
    start_encoding_request = StartEncodingRequest()
    _execute_encoding(encoding=encoding, start_encoding_request=start_encoding_request)

    dash_manifest = _create_dash_manifest_audio_only(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)
    hls_manifest = _create_hls_manifest_audio_only(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)
    _execute_dash_manifest_generation(dash_manifest=dash_manifest)
    _execute_hls_manifest_generation(hls_manifest=hls_manifest)


def _execute_encoding(encoding, start_encoding_request):
    bitmovin_api.encoding.encodings.start(encoding_id=encoding.id, start_encoding_request=start_encoding_request)

    task = _wait_for_enoding_to_finish(encoding_id=encoding.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_enoding_to_finish(encoding_id=encoding.id)

    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("Encoding failed")

    print("Encoding finished successfully")


def _create_dash_manifest_audio_only(encoding_id, output, output_path):
    manifest_output = EncodingOutput(output_id=output.id,
                                     output_path=output_path,
                                     acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])
    dash_manifest = bitmovin_api.encoding.manifests.dash.create(
        dash_manifest=DashManifest(
            manifest_name='stream.mpd',
            outputs=[manifest_output],
            name='DASH Manifest'))
    period = bitmovin_api.encoding.manifests.dash.periods.create(
        manifest_id=dash_manifest.id,
        period=Period())
    audio_adaptation_set = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.audio.create(
        audio_adaptation_set=AudioAdaptationSet(lang='en'),
        manifest_id=dash_manifest.id,
        period_id=period.id)

    fmp4_muxings = bitmovin_api.encoding.encodings.muxings.fmp4.list(encoding_id=encoding_id)
    for muxing in fmp4_muxings.items:
        stream = bitmovin_api.encoding.encodings.streams.get(
            encoding_id=encoding_id, stream_id=muxing.streams[0].stream_id)

        if 'PER_TITLE_TEMPLATE' in stream.mode.value:
            continue

        codec = bitmovin_api.encoding.configurations.type.get(configuration_id=stream.codec_config_id)
        segment_path = _remove_output_base_path(muxing.outputs[0].output_path)

        if codec.type == CodecConfigType.DOLBY_ATMOS:
            bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
                manifest_id=dash_manifest.id,
                period_id=period.id,
                adaptationset_id=audio_adaptation_set.id,
                dash_fmp4_representation=DashFmp4Representation(
                    encoding_id=encoding_id,
                    muxing_id=muxing.id,
                    type_=DashRepresentationType.TEMPLATE,
                    mode=DashRepresentationTypeMode.TEMPLATE_REPRESENTATION,
                    segment_path=segment_path))
    return dash_manifest


def _create_hls_manifest_audio_only(encoding_id, output, output_path):
    manifest_output = EncodingOutput(output_id=output.id,
                                     output_path=output_path,
                                     acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])

    hls_manifest = bitmovin_api.encoding.manifests.hls.create(
        hls_manifest=HlsManifest(
            manifest_name='stream.m3u8',
            outputs=[manifest_output],
            name='HLS Manifest',
            hls_master_playlist_version=HlsVersion.HLS_V8,
            hls_media_playlist_version=HlsVersion.HLS_V8))

    fmp4_muxings = bitmovin_api.encoding.encodings.muxings.fmp4.list(encoding_id=encoding_id)
    for muxing in fmp4_muxings.items:
        stream = bitmovin_api.encoding.encodings.streams.get(
            encoding_id=encoding_id, stream_id=muxing.streams[0].stream_id)

        if 'PER_TITLE_TEMPLATE' in stream.mode.value:
            continue

        codec = bitmovin_api.encoding.configurations.type.get(configuration_id=stream.codec_config_id)
        segment_path = _remove_output_base_path(muxing.outputs[0].output_path)

        if codec.type == CodecConfigType.DOLBY_ATMOS:
            audio_codec = bitmovin_api.encoding.configurations.audio.dolby_atmos.get(
                configuration_id=stream.codec_config_id)
            bitmovin_api.encoding.manifests.hls.media.audio.create(
                manifest_id=hls_manifest.id,
                audio_media_info=AudioMediaInfo(
                    name='HLS Audio Media',
                    group_id='audio',
                    language='en',
                    segment_path=segment_path,
                    encoding_id=encoding_id,
                    stream_id=stream.id,
                    muxing_id=muxing.id,
                    uri='audio_{}.m3u8'.format(audio_codec.bitrate)))

            bitmovin_api.encoding.manifests.hls.streams.create(
                manifest_id=hls_manifest.id,
                stream_info=StreamInfo(
                    audio='audio',
                    closed_captions='NONE',
                    segment_path=segment_path,
                    uri='audio_{}.m3u8'.format(audio_codec.bitrate),
                    encoding_id=encoding_id,
                    stream_id=stream.id,
                    muxing_id=muxing.id))
    return hls_manifest


def _execute_dash_manifest_generation(dash_manifest):
    bitmovin_api.encoding.manifests.dash.start(manifest_id=dash_manifest.id)

    task = _wait_for_dash_manifest_to_finish(manifest_id=dash_manifest.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_dash_manifest_to_finish(manifest_id=dash_manifest.id)
    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("DASH Manifest Creation failed")

    print("DASH Manifest Creation finished successfully")


def _execute_hls_manifest_generation(hls_manifest):
    bitmovin_api.encoding.manifests.hls.start(manifest_id=hls_manifest.id)

    task = _wait_for_hls_manifest_to_finish(manifest_id=hls_manifest.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_hls_manifest_to_finish(manifest_id=hls_manifest.id)
    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("HLS Manifest Creation failed")

    print("HLS Manifest Creation finished successfully")


def _wait_for_enoding_to_finish(encoding_id):
    time.sleep(5)
    task = bitmovin_api.encoding.encodings.status(encoding_id=encoding_id)
    print("Encoding status is {} (progress: {} %)".format(task.status, task.progress))
    return task


def _wait_for_dash_manifest_to_finish(manifest_id):
    time.sleep(5)
    task = bitmovin_api.encoding.manifests.dash.status(manifest_id=manifest_id)
    print("DASH manifest status is {} (progress: {} %)".format(task.status, task.progress))
    return task


def _wait_for_hls_manifest_to_finish(manifest_id):
    time.sleep(5)
    task = bitmovin_api.encoding.manifests.hls.status(manifest_id=manifest_id)
    print("HLS manifest status is {} (progress: {} %)".format(task.status, task.progress))
    return task


def _remove_output_base_path(text):
    if text.startswith(OUTPUT_BASE_PATH):
        return text[len(OUTPUT_BASE_PATH):]
    return text


def _log_task_errors(task):
    if task is None:
        return

    filtered = filter(lambda msg: msg.type is MessageType.ERROR, task.messages)

    for message in filtered:
        print(message.text)


if __name__ == '__main__':
    main()
