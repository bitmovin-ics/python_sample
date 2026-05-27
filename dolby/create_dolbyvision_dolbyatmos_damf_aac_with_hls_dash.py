import time

from bitmovin_api_sdk import BitmovinApi
from bitmovin_api_sdk import S3Input, S3Output
from bitmovin_api_sdk import Encoding, CloudRegion
from bitmovin_api_sdk import EncodingOutput, AclEntry, AclPermission
from bitmovin_api_sdk import DolbyVisionInputStream, IngestInputStream, StreamSelectionMode
from bitmovin_api_sdk import Stream, StreamInput, MuxingStream, StreamMode
from bitmovin_api_sdk import DolbyAtmosAudioConfiguration, DolbyAtmosLoudnessControl, DolbyAtmosMeteringMode
from bitmovin_api_sdk import DolbyAtmosDialogueIntelligence, DolbyAtmosIngestInputStream, DolbyAtmosInputFormat
from bitmovin_api_sdk import AacAudioConfiguration, AacChannelLayout
from bitmovin_api_sdk import H265VideoConfiguration, CodecConfigType
from bitmovin_api_sdk import H265DynamicRangeFormat, MaxCtuSize, MotionSearch, TuInterDepth, TuIntraDepth
from bitmovin_api_sdk import AdaptiveQuantMode
from bitmovin_api_sdk import Fmp4Muxing
from bitmovin_api_sdk import DashManifest, Period, VideoAdaptationSet, AudioAdaptationSet
from bitmovin_api_sdk import DashFmp4Representation, DashRepresentationType, DashRepresentationTypeMode
from bitmovin_api_sdk import HlsManifest, HlsVersion, AudioMediaInfo, StreamInfo, IFramePlaylist
from bitmovin_api_sdk import MessageType, StartEncodingRequest, ManifestResource, ManifestGenerator
from bitmovin_api_sdk import Status

TEST_ITEM = "dolbyvision-dolbyatmos-damf-aac-hls-dash-fmp4"

API_KEY = '<INSERT YOUR API KEY>'
ORG_ID = '<INSERT YOUR ORG ID>'

S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

S3_OUTPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_OUTPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_OUTPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

# Dolby Vision video + sidecar metadata.
# (Reference assets are available from Netflix Open Content: https://opencontent.netflix.com/ — Sol Levante)
DOLBY_VISION_INPUT_PATH = '<INSERT_DOLBY_VISION_VIDEO_PATH>'
DOLBY_VISION_INPUT_METADATA = '<INSERT_DOLBY_VISION_METADATA_PATH>'

# Dolby Atmos DAMF mezzanine
DOLBY_ATMOS_DAMF_PATH = '<INSERT_DOLBY_ATMOS_DAMF_PATH>'

# AAC stereo mezzanine (universal fallback per HLS Authoring Spec)
AAC_2_0_INPUT_PATH = '<INSERT_AAC_2_0_MEZZANINE_PATH>'

OUTPUT_BASE_PATH = f'output/{TEST_ITEM}/'

bitmovin_api = BitmovinApi(api_key=API_KEY, tenant_org_id=ORG_ID)

# Video ladder. Dolby Vision (HDR) only — no SDR fallback in this configuration.
encoding_profiles_video = [
    {"height": 2160, "bitrate": 15_000_000, "aqs": 0.5},
    {"height": 1080, "bitrate": 6_000_000, "aqs": 0.8},
    {"height": 720, "bitrate": 3_000_000, "aqs": 1.0},
    {"height": 540, "bitrate": 1_800_000, "aqs": 1.2},
]

# Audio renditions: Atmos premium + AAC stereo universal fallback.
# `codec` discriminates the codec config / ingest type used in the loop below.
# Source mezzanine paths are taken directly from the top-level constants
# (DOLBY_ATMOS_DAMF_PATH / AAC_2_0_INPUT_PATH).
encoding_profiles_audio = [
    {"codec": "atmos", "bitrate": 448_000, "rate": 48_000},
    {"codec": "aac", "bitrate": 128_000, "rate": 48_000, "channel_layout": AacChannelLayout.CL_STEREO},
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

    # === Input Streams ===
    # DolbyVisionInputStream — the encoder derives the DV renditions from this single input.
    dv_video_ingest = bitmovin_api.encoding.encodings.input_streams.dolby_vision.create(
        encoding_id=encoding.id,
        dolby_vision_input_stream=DolbyVisionInputStream(
            input_id=s3_input.id,
            video_input_path=DOLBY_VISION_INPUT_PATH,
            metadata_input_path=DOLBY_VISION_INPUT_METADATA))
    video_input_stream = StreamInput(input_stream_id=dv_video_ingest.id)

    # === Video codec configs + streams + muxings (DV ladder) ===
    for profile in encoding_profiles_video:
        h265_codec = bitmovin_api.encoding.configurations.video.h265.create(
            h265_video_configuration=H265VideoConfiguration(
                name=f"H265 DV {profile['height']}p",
                height=profile["height"],
                bitrate=profile["bitrate"],
                max_bitrate=profile["bitrate"] * 2,
                bufsize=profile["bitrate"] * 4,
                dynamic_range_format=H265DynamicRangeFormat.DOLBY_VISION,
                max_keyframe_interval=2,
                min_keyframe_interval=2,
                rc_lookahead=60,
                sub_me=5,
                max_ctu_size=MaxCtuSize.S64,
                motion_search=MotionSearch.STAR,
                tu_intra_depth=TuIntraDepth.D4,
                tu_inter_depth=TuInterDepth.D4,
                weight_prediction_on_p_slice=True,
                weight_prediction_on_b_slice=True,
                scene_cut_threshold=40,
                motion_search_range=92,
                adaptive_quantization_mode=AdaptiveQuantMode.AUTO_VARIANCE_DARK_SCENES,
                adaptive_quantization_strength=profile["aqs"],
                psy_rate_distortion_optimization=0,
                psy_rate_distortion_optimized_quantization=0,
                qp_min=15,
                sao=True))

        video_stream = bitmovin_api.encoding.encodings.streams.create(
            encoding_id=encoding.id,
            stream=Stream(
                codec_config_id=h265_codec.id,
                input_streams=[video_input_stream],
                name=f"Stream H265 DV {profile['height']}p",
                mode=StreamMode.STANDARD))

        bitmovin_api.encoding.encodings.muxings.fmp4.create(
            encoding_id=encoding.id,
            fmp4_muxing=Fmp4Muxing(
                segment_length=6,
                segment_naming='seg_%number%.m4s',
                init_segment_name='init.mp4',
                streams=[MuxingStream(stream_id=video_stream.id)],
                outputs=[EncodingOutput(
                    output_id=s3_output.id,
                    output_path=f"{OUTPUT_BASE_PATH}video/dv/{profile['height']}p_{profile['bitrate']}/",
                    acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])],
                name=f"Video FMP4 DV {profile['height']}p"))

    # === Audio codec configs + streams + muxings (Atmos + AAC stereo) ===
    for profile in encoding_profiles_audio:
        if profile["codec"] == "atmos":
            ingest = bitmovin_api.encoding.encodings.input_streams.dolby_atmos.create(
                encoding_id=encoding.id,
                dolby_atmos_ingest_input_stream=DolbyAtmosIngestInputStream(
                    input_id=s3_input.id,
                    input_path=DOLBY_ATMOS_DAMF_PATH,
                    input_format=DolbyAtmosInputFormat.DAMF))
            audio_codec = bitmovin_api.encoding.configurations.audio.dolby_atmos.create(
                dolby_atmos_audio_configuration=DolbyAtmosAudioConfiguration(
                    bitrate=profile["bitrate"],
                    rate=profile["rate"],
                    loudness_control=DolbyAtmosLoudnessControl(
                        metering_mode=DolbyAtmosMeteringMode.ITU_R_BS_1770_4,
                        dialogue_intelligence=DolbyAtmosDialogueIntelligence.ENABLED,
                        speech_threshold=15)))
            label = 'atmos'
        elif profile["codec"] == "aac":
            ingest = bitmovin_api.encoding.encodings.input_streams.ingest.create(
                encoding_id=encoding.id,
                ingest_input_stream=IngestInputStream(
                    input_id=s3_input.id,
                    input_path=AAC_2_0_INPUT_PATH,
                    selection_mode=StreamSelectionMode.AUDIO_RELATIVE,
                    position=0))
            audio_codec = bitmovin_api.encoding.configurations.audio.aac.create(
                aac_audio_configuration=AacAudioConfiguration(
                    name=f"AAC {profile['bitrate']}bps",
                    bitrate=profile["bitrate"],
                    rate=profile["rate"],
                    channel_layout=profile["channel_layout"]))
            label = 'aac'
        else:
            continue

        audio_input_stream = StreamInput(input_stream_id=ingest.id)
        audio_stream = bitmovin_api.encoding.encodings.streams.create(
            encoding_id=encoding.id,
            stream=Stream(
                codec_config_id=audio_codec.id,
                input_streams=[audio_input_stream],
                name=f"Stream {label.upper()} {profile['bitrate']}bps",
                mode=StreamMode.STANDARD))

        bitmovin_api.encoding.encodings.muxings.fmp4.create(
            encoding_id=encoding.id,
            fmp4_muxing=Fmp4Muxing(
                segment_length=6,
                segment_naming='seg_%number%.m4s',
                init_segment_name='init.mp4',
                streams=[MuxingStream(stream_id=audio_stream.id)],
                outputs=[EncodingOutput(
                    output_id=s3_output.id,
                    output_path=f"{OUTPUT_BASE_PATH}audio/{label}/{profile['bitrate']}/",
                    acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])],
                name=f"Audio FMP4 {label.upper()} {profile['bitrate']}bps"))

    # === Manifests are created before encoding starts; V2 generator finalizes them. ===
    dash_manifest = _create_dash_manifest(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)
    hls_manifest = _create_hls_manifest(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)

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


def _create_dash_manifest(encoding_id, output, output_path):
    """DASH manifest. AdaptationSets: one for DV video, one each for Atmos and AAC stereo
    audio. Modern players auto-select between Atmos and AAC based on codec capability.
    The V2 generator is expected to populate `Role main` and the EC-3 JOC SupplementalProperty
    descriptors; inspect the generated MPD and patch here if missing."""
    manifest_output = EncodingOutput(
        output_id=output.id,
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

    video_as = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.video.create(
        video_adaptation_set=VideoAdaptationSet(),
        manifest_id=dash_manifest.id,
        period_id=period.id)
    audio_as_atmos = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.audio.create(
        audio_adaptation_set=AudioAdaptationSet(lang='en'),
        manifest_id=dash_manifest.id,
        period_id=period.id)
    audio_as_aac = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.audio.create(
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

        if codec.type == CodecConfigType.H265:
            adaptationset_id = video_as.id
        elif codec.type == CodecConfigType.DOLBY_ATMOS:
            adaptationset_id = audio_as_atmos.id
        elif codec.type == CodecConfigType.AAC:
            adaptationset_id = audio_as_aac.id
        else:
            continue

        bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
            manifest_id=dash_manifest.id,
            period_id=period.id,
            adaptationset_id=adaptationset_id,
            dash_fmp4_representation=DashFmp4Representation(
                encoding_id=encoding_id,
                muxing_id=muxing.id,
                type_=DashRepresentationType.TEMPLATE,
                mode=DashRepresentationTypeMode.TEMPLATE_REPRESENTATION,
                segment_path=segment_path))

    return dash_manifest


def _create_hls_manifest(encoding_id, output, output_path):
    """HLS manifest. Two audio groups (`aac` default + `atmos` premium); each video rendition
    is exposed as TWO variants (paired with each audio group) plus one #EXT-X-I-FRAME-STREAM-INF
    entry for trick-play. V2 generator populates VIDEO-RANGE / CODECS / CHANNELS attributes."""
    manifest_output = EncodingOutput(
        output_id=output.id,
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
            atmos_codec = bitmovin_api.encoding.configurations.audio.dolby_atmos.get(
                configuration_id=stream.codec_config_id)
            # The actual audio rendition picked at playback is driven by the variant's AUDIO= attribute
            # (each video variant is paired with one audio group below). DEFAULT/AUTOSELECT here only
            # affect UX hints inside the group; we keep them explicit for spec clarity.
            bitmovin_api.encoding.manifests.hls.media.audio.create(
                manifest_id=hls_manifest.id,
                audio_media_info=AudioMediaInfo(
                    name='English Atmos',
                    group_id='atmos',
                    language='en',
                    is_default=False,
                    autoselect=True,
                    segment_path=segment_path,
                    encoding_id=encoding_id,
                    stream_id=stream.id,
                    muxing_id=muxing.id,
                    uri=f'audio_atmos_{atmos_codec.bitrate}.m3u8'))

        elif codec.type == CodecConfigType.AAC:
            audio_codec = bitmovin_api.encoding.configurations.audio.aac.get(
                configuration_id=stream.codec_config_id)
            bitmovin_api.encoding.manifests.hls.media.audio.create(
                manifest_id=hls_manifest.id,
                audio_media_info=AudioMediaInfo(
                    name='English AAC',
                    group_id='aac',
                    language='en',
                    is_default=True,
                    autoselect=True,
                    segment_path=segment_path,
                    encoding_id=encoding_id,
                    stream_id=stream.id,
                    muxing_id=muxing.id,
                    uri=f'audio_aac_{audio_codec.bitrate}.m3u8'))

        elif codec.type == CodecConfigType.H265:
            video_codec = bitmovin_api.encoding.configurations.video.h265.get(configuration_id=stream.codec_config_id)

            # Two variants per video rendition (one per audio group). URIs include height to stay
            # unique even if the ladder ever has two entries at the same bitrate.
            variants = []
            for audio_group in ('aac', 'atmos'):
                variant = bitmovin_api.encoding.manifests.hls.streams.create(
                    manifest_id=hls_manifest.id,
                    stream_info=StreamInfo(
                        audio=audio_group,
                        closed_captions='NONE',
                        segment_path=segment_path,
                        uri=f'video_dv_{video_codec.height}p_{video_codec.bitrate}_{audio_group}.m3u8',
                        encoding_id=encoding_id,
                        stream_id=stream.id,
                        muxing_id=muxing.id))
                variants.append(variant)

            # One I-Frame playlist per video rendition (Apple trick-play requirement).
            # The playlist is attached to one of the variants; it references the same video segments.
            bitmovin_api.encoding.manifests.hls.streams.iframe.create(
                manifest_id=hls_manifest.id,
                stream_id=variants[0].id,
                i_frame_playlist=IFramePlaylist(
                    filename=f'video_dv_{video_codec.height}p_{video_codec.bitrate}_iframe.m3u8'))

    return hls_manifest


def _wait_for_encoding_to_finish(encoding_id):
    time.sleep(5)
    task = bitmovin_api.encoding.encodings.status(encoding_id=encoding_id)
    print(f"Encoding status is {task.status} (progress: {task.progress} %)")
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
