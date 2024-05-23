import time

from bitmovin_api_sdk import BitmovinApi
from bitmovin_api_sdk import S3Input, S3Output
from bitmovin_api_sdk import Encoding, CloudRegion
from bitmovin_api_sdk import EncodingOutput, AclEntry, AclPermission
from bitmovin_api_sdk import IngestInputStream, StreamSelectionMode, PresetConfiguration
from bitmovin_api_sdk import Stream, StreamInput, MuxingStream, StreamMode
from bitmovin_api_sdk import AacAudioConfiguration, AacChannelLayout
from bitmovin_api_sdk import H264VideoConfiguration, CodecConfigType
from bitmovin_api_sdk import Fmp4Muxing
from bitmovin_api_sdk import CencDrm, CencWidevine, CencPlayReady, CencFairPlay, IvSize, EncryptionMode
from bitmovin_api_sdk import ContentProtection
from bitmovin_api_sdk import Condition, ConditionOperator
from bitmovin_api_sdk import DashManifest, Period, VideoAdaptationSet, AudioAdaptationSet
from bitmovin_api_sdk import DashFmp4Representation, DashRepresentationType, DashRepresentationTypeMode
from bitmovin_api_sdk import HlsManifest, HlsVersion, AudioMediaInfo, StreamInfo
from bitmovin_api_sdk import MessageType, StartEncodingRequest, ManifestResource, ManifestGenerator
from bitmovin_api_sdk import Status

TEST_ITEM = "cenc-cbc-drm-wv-pr-fp-dash-hls-aws"

API_KEY = '<INSERT YOUR API KEY>'
ORG_ID = '<INSERT YOUR ORG ID>'

S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

INPUT_PATH = "{YOUR INPUT FILE PATH}"  # "big_buck_bunny_1080p_h264.mov"

S3_OUTPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_OUTPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_OUTPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

OUTPUT_BASE_PATH = f'output/{TEST_ITEM}/'

CENC_KEY = '12341234123412341234123412341234'
CENC_KID = '43214321432143214321432143214321'
CENC_WIDEVINE_PSSH = 'CAESEAABAgMEBQYHCAkKCwwNDg8aCmludGVydHJ1c3QiASo='
CENC_PLAYREADY_LA_URL = 'http://pr.test.drm.com/playready/RightsManager.asmx'
CENC_FAIRPLAY_IV = '00000000000000000000000000000000'
CENC_FAIRPLAY_URI = 'skd://fairplay_token'

bitmovin_api = BitmovinApi(api_key=API_KEY, tenant_org_id=ORG_ID)

encoding_profiles_h264 = [
    dict(height=1080, bitrate=2_500_000, level=None, mode=StreamMode.STANDARD),
    dict(height=720, bitrate=1_200_000, level=None, mode=StreamMode.STANDARD),
    dict(height=480, bitrate=750_000, level=None, mode=StreamMode.STANDARD),
    dict(height=360, bitrate=400_000, level=None, mode=StreamMode.STANDARD),
    dict(height=240, bitrate=150_000, level=None, mode=StreamMode.STANDARD)
]

encoding_profiles_aac = [
    dict(bitrate=128000, rate=48_000)
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
            name=f'{TEST_ITEM}',
            cloud_region=CloudRegion.AWS_AP_NORTHEAST_1,
            encoder_version='STABLE'))

    # === Input Stream definition for video and audio ===
    video_ingest_input_stream = bitmovin_api.encoding.encodings.input_streams.ingest.create(
        encoding_id=encoding.id,
        ingest_input_stream=IngestInputStream(
            input_id=s3_input.id,
            input_path=INPUT_PATH,
            selection_mode=StreamSelectionMode.VIDEO_RELATIVE,
            position=0))
    audio_ingest_input_stream = bitmovin_api.encoding.encodings.input_streams.ingest.create(
        encoding_id=encoding.id,
        ingest_input_stream=IngestInputStream(
            input_id=s3_input.id,
            input_path=INPUT_PATH,
            selection_mode=StreamSelectionMode.AUDIO_RELATIVE,
            position=0))

    video_input_stream = StreamInput(input_stream_id=video_ingest_input_stream.id)
    audio_input_stream = StreamInput(input_stream_id=audio_ingest_input_stream.id)

    # === Video Profile definition ===
    for profile_h264 in encoding_profiles_h264:
        h264_codec = bitmovin_api.encoding.configurations.video.h264.create(
            h264_video_configuration=H264VideoConfiguration(
                name='Sample video codec configuration',
                height=profile_h264.get("height"),
                bitrate=profile_h264.get("bitrate"),
                preset_configuration=PresetConfiguration.VOD_HIGH_QUALITY))

        # Create Video Stream
        h264_stream = bitmovin_api.encoding.encodings.streams.create(
            encoding_id=encoding.id,
            stream=Stream(
                codec_config_id=h264_codec.id,
                input_streams=[video_input_stream],
                name=f"Stream H264 {profile_h264.get('height')}p",
                mode=profile_h264.get('mode')))

        # Create Fmp4 muxing output path
        video_muxing_output = EncodingOutput(
            output_id=s3_output.id,
            output_path=f"{OUTPUT_BASE_PATH}video/{profile_h264.get('height')}p",
            acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])

        # Create Fmp4 muxing without specifying output
        fmp4_muxing = bitmovin_api.encoding.encodings.muxings.fmp4.create(
            encoding_id=encoding.id,
            fmp4_muxing=Fmp4Muxing(
                segment_length=6,
                segment_naming='segment_%number%.m4s',
                init_segment_name='init.mp4',
                streams=[MuxingStream(stream_id=h264_stream.id)],
                name=f"Video FMP4 Muxing {profile_h264.get('height')}p"))

        # Cenc CBC DRM with output
        bitmovin_api.encoding.encodings.muxings.fmp4.drm.cenc.create(
            encoding_id=encoding.id,
            muxing_id=fmp4_muxing.id,
            cenc_drm=CencDrm(
                key=CENC_KEY,
                kid=CENC_KID,
                widevine=CencWidevine(pssh=CENC_WIDEVINE_PSSH),
                play_ready=CencPlayReady(la_url=CENC_PLAYREADY_LA_URL),
                fair_play=CencFairPlay(
                    iv=CENC_FAIRPLAY_IV,
                    uri=CENC_FAIRPLAY_URI
                ),
                encryption_mode=EncryptionMode.CBC,
                outputs=[video_muxing_output],
                name="Video FMP4 CENC",
                iv_size=IvSize.IV_16_BYTES
            )
        )

    # === Audio Profile definition ===
    for profile_aac in encoding_profiles_aac:
        aac_codec = bitmovin_api.encoding.configurations.audio.aac.create(
            aac_audio_configuration=AacAudioConfiguration(
                bitrate=profile_aac.get("bitrate"),
                rate=profile_aac.get("rate"),
                channel_layout=AacChannelLayout.CL_STEREO))

        # Create Audio Stream
        aac_stream = bitmovin_api.encoding.encodings.streams.create(
            encoding_id=encoding.id,
            stream=Stream(
                codec_config_id=aac_codec.id,
                input_streams=[audio_input_stream],
                name=f"Stream AAC {profile_aac.get('bitrate') / 1000:.0f}kbps",
                conditions=Condition(
                    attribute="AUDIOSTREAMCOUNT",
                    operator=ConditionOperator.GREATER_THAN,
                    value="0"
                ),
                mode=StreamMode.STANDARD))

        # Create Fmp4 muxing output path
        audio_muxing_output = EncodingOutput(
            output_id=s3_output.id,
            output_path=f"{OUTPUT_BASE_PATH}audio/{profile_aac.get('bitrate')}",
            acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])

        # Create Fmp4 muxing without specifying output
        fmp4_muxing = bitmovin_api.encoding.encodings.muxings.fmp4.create(
            encoding_id=encoding.id,
            fmp4_muxing=Fmp4Muxing(
                segment_length=6,
                segment_naming='segment_%number%.m4s',
                init_segment_name='init.mp4',
                streams=[MuxingStream(stream_id=aac_stream.id)],
                name=f"Audio FMP4 Muxing {profile_aac.get('bitrate') / 1000:.0f}kbps"))

        # Cenc CBC DRM with output
        bitmovin_api.encoding.encodings.muxings.fmp4.drm.cenc.create(
            encoding_id=encoding.id,
            muxing_id=fmp4_muxing.id,
            cenc_drm=CencDrm(
                key=CENC_KEY,
                kid=CENC_KID,
                widevine=CencWidevine(pssh=CENC_WIDEVINE_PSSH),
                play_ready=CencPlayReady(la_url=CENC_PLAYREADY_LA_URL),
                fair_play=CencFairPlay(
                    iv=CENC_FAIRPLAY_IV,
                    uri=CENC_FAIRPLAY_URI
                ),
                encryption_mode=EncryptionMode.CBC,
                outputs=[audio_muxing_output],
                name="Audio FMP4 CENC",
                iv_size=IvSize.IV_16_BYTES
            )
        )

    # === Start Encoding settings together with HLS Manifest definition ===
    hls_manifest = _create_hls_manifest(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)
    dash_manifest = _create_dash_manifest(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)
    start_encoding_request = StartEncodingRequest(
        vod_dash_manifests=[ManifestResource(manifest_id=dash_manifest.id)],
        vod_hls_manifests=[ManifestResource(manifest_id=hls_manifest.id)],
        manifest_generator=ManifestGenerator.V2)
    _execute_encoding(encoding=encoding, start_encoding_request=start_encoding_request)


def _execute_encoding(encoding, start_encoding_request):
    bitmovin_api.encoding.encodings.start(encoding_id=encoding.id, start_encoding_request=start_encoding_request)

    task = _wait_for_encoding_to_finish(encoding_id=encoding.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_encoding_to_finish(encoding_id=encoding.id)

    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("Encoding failed")

    print("Encoding finished successfully")


def _create_hls_manifest(encoding_id, output, output_path):
    manifest_output = EncodingOutput(output_id=output.id,
                                     output_path=output_path,
                                     acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])

    hls_manifest = bitmovin_api.encoding.manifests.hls.create(
        hls_manifest=HlsManifest(
            manifest_name='stream.m3u8',
            outputs=[manifest_output],
            name='HLS Manifest',
            hls_master_playlist_version=HlsVersion.HLS_V6,
            hls_media_playlist_version=HlsVersion.HLS_V6))

    fmp4_muxings = bitmovin_api.encoding.encodings.muxings.fmp4.list(encoding_id=encoding_id)
    for muxing in fmp4_muxings.items:
        stream = bitmovin_api.encoding.encodings.streams.get(
            encoding_id=encoding_id, stream_id=muxing.streams[0].stream_id)

        if 'PER_TITLE_TEMPLATE' in stream.mode.value:
            continue

        codec = bitmovin_api.encoding.configurations.type.get(configuration_id=stream.codec_config_id)
        drm = bitmovin_api.encoding.encodings.muxings.fmp4.drm.cenc.list(
            encoding_id=encoding_id,
            muxing_id=muxing.id
        ).items
        segment_path = _remove_output_base_path(drm[0].outputs[0].output_path)

        if codec.type == CodecConfigType.AAC:
            audio_codec = bitmovin_api.encoding.configurations.audio.aac.get(
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
                    drm_id=drm[0].id,
                    uri=f'audio_{audio_codec.bitrate}.m3u8'))

        elif codec.type == CodecConfigType.H264:
            video_codec = bitmovin_api.encoding.configurations.video.h264.get(configuration_id=stream.codec_config_id)
            bitmovin_api.encoding.manifests.hls.streams.create(
                manifest_id=hls_manifest.id,
                stream_info=StreamInfo(
                    audio='audio',
                    closed_captions='NONE',
                    segment_path=segment_path,
                    uri=f'video_{video_codec.bitrate}.m3u8',
                    encoding_id=encoding_id,
                    stream_id=stream.id,
                    muxing_id=muxing.id,
                    drm_id=drm[0].id))

    return hls_manifest


def _create_dash_manifest(encoding_id, output, output_path):
    manifest_output = EncodingOutput(
        output_id=output.id,
        output_path=output_path,
        acl=[AclEntry(permission=AclPermission.PUBLIC_READ)]
    )
    dash_manifest = bitmovin_api.encoding.manifests.dash.create(
        dash_manifest=DashManifest(
            manifest_name='stream.mpd',
            outputs=[manifest_output],
            name='DASH Manifest'
        )
    )
    period = bitmovin_api.encoding.manifests.dash.periods.create(
        manifest_id=dash_manifest.id,
        period=Period()
    )
    video_adaptation_set = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.video.create(
        video_adaptation_set=VideoAdaptationSet(),
        manifest_id=dash_manifest.id,
        period_id=period.id
    )
    audio_adaptation_set = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.audio.create(
        audio_adaptation_set=AudioAdaptationSet(lang='en'),
        manifest_id=dash_manifest.id,
        period_id=period.id
    )

    fmp4_muxings = bitmovin_api.encoding.encodings.muxings.fmp4.list(encoding_id=encoding_id)
    for muxing in fmp4_muxings.items:
        stream = bitmovin_api.encoding.encodings.streams.get(
            encoding_id=encoding_id, stream_id=muxing.streams[0].stream_id)

        if 'PER_TITLE_TEMPLATE' in stream.mode.value:
            continue

        codec = bitmovin_api.encoding.configurations.type.get(configuration_id=stream.codec_config_id)
        drm = bitmovin_api.encoding.encodings.muxings.fmp4.drm.cenc.list(
            encoding_id=encoding_id,
            muxing_id=muxing.id
        ).items
        segment_path = _remove_output_base_path(drm[0].outputs[0].output_path)

        if codec.type == CodecConfigType.AAC:
            representation = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
                manifest_id=dash_manifest.id,
                period_id=period.id,
                adaptationset_id=audio_adaptation_set.id,
                dash_fmp4_representation=DashFmp4Representation(
                    encoding_id=encoding_id,
                    muxing_id=muxing.id,
                    type_=DashRepresentationType.TEMPLATE,
                    mode=DashRepresentationTypeMode.TEMPLATE_REPRESENTATION,
                    segment_path=segment_path
                )
            )
            bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.contentprotection.create(
                manifest_id=dash_manifest.id,
                period_id=period.id,
                adaptationset_id=audio_adaptation_set.id,
                representation_id=representation.id,
                content_protection=ContentProtection(
                    encoding_id=encoding_id,
                    muxing_id=muxing.id,
                    drm_id=drm[0].id))

        elif codec.type == CodecConfigType.H264:
            representation = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
                manifest_id=dash_manifest.id,
                period_id=period.id,
                adaptationset_id=video_adaptation_set.id,
                dash_fmp4_representation=DashFmp4Representation(
                    encoding_id=encoding_id,
                    muxing_id=muxing.id,
                    type_=DashRepresentationType.TEMPLATE,
                    mode=DashRepresentationTypeMode.TEMPLATE_REPRESENTATION,
                    segment_path=segment_path
                )
            )
            bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.contentprotection.create(
                manifest_id=dash_manifest.id,
                period_id=period.id,
                adaptationset_id=video_adaptation_set.id,
                representation_id=representation.id,
                content_protection=ContentProtection(
                    encoding_id=encoding_id,
                    muxing_id=muxing.id,
                    drm_id=drm[0].id))
    return dash_manifest


def _execute_hls_manifest_generation(hls_manifest):
    bitmovin_api.encoding.manifests.hls.start(manifest_id=hls_manifest.id)

    task = _wait_for_hls_manifest_to_finish(manifest_id=hls_manifest.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_hls_manifest_to_finish(manifest_id=hls_manifest.id)
    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("HLS Manifest Creation failed")

    print("DASH Manifest Creation finished successfully")


def _wait_for_encoding_to_finish(encoding_id):
    time.sleep(5)
    task = bitmovin_api.encoding.encodings.status(encoding_id=encoding_id)
    print(f"Encoding status is {task.status} (progress: {task.progress} %)")
    return task


def _wait_for_hls_manifest_to_finish(manifest_id):
    time.sleep(5)
    task = bitmovin_api.encoding.manifests.hls.status(manifest_id=manifest_id)
    print(f"HLS manifest status is {task.status} (progress: {task.progress} %)")
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
