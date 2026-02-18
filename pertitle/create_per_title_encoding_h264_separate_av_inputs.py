import time

from bitmovin_api_sdk import BitmovinApi
from bitmovin_api_sdk import S3Input, S3Output
from bitmovin_api_sdk import Encoding, CloudRegion, EncodingMode
from bitmovin_api_sdk import EncodingOutput, AclEntry, AclPermission
from bitmovin_api_sdk import IngestInputStream, StreamSelectionMode
from bitmovin_api_sdk import Stream, StreamInput, MuxingStream, StreamMode
from bitmovin_api_sdk import H264VideoConfiguration, ProfileH264, AacChannelLayout
from bitmovin_api_sdk import H264MotionEstimationMethod, MvPredictionMode, AdaptiveQuantMode
from bitmovin_api_sdk import ColorConfig, CodecConfigType, H264Trellis, H264SubMe
from bitmovin_api_sdk import AacAudioConfiguration
from bitmovin_api_sdk import Fmp4Muxing, TsMuxing
from bitmovin_api_sdk import MessageType, StartEncodingRequest
from bitmovin_api_sdk import HlsVersion, DashManifest, Period
from bitmovin_api_sdk import VideoAdaptationSet, AudioAdaptationSet
from bitmovin_api_sdk import DashFmp4Representation, DashRepresentationType
from bitmovin_api_sdk import HlsManifest, AudioMediaInfo, StreamInfo
from bitmovin_api_sdk import StreamPerTitleFixedResolutionAndBitrateSettings, BitrateSelectionMode
from bitmovin_api_sdk import PerTitle, PerTitleFixedResolutionAndBitrateConfiguration
from bitmovin_api_sdk import PerTitleFixedResolutionAndBitrateConfigurationMode
from bitmovin_api_sdk import StreamPerTitleSettings, H264PerTitleConfiguration
from bitmovin_api_sdk import StartManifestRequest, ManifestGenerator
from bitmovin_api_sdk import Status

TEST_ITEM = "vod-pertitle-h264-aac-ts-fmp4-hls-dash"

API_KEY = '<INSERT YOUR API KEY>'
ORG_ID = '<INSERT YOUR ORG ID>'

S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

# Separate input files: video-only (mp4) and audio-only (wav)
VIDEO_INPUT_PATH = '/path/to/your/input/video_only.mp4'
AUDIO_INPUT_PATH = '/path/to/your/input/audio_only.wav'

S3_OUTPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_OUTPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_OUTPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

OUTPUT_BASE_PATH = f'output/{TEST_ITEM}/'

bitmovin_api = BitmovinApi(api_key=API_KEY, tenant_org_id=ORG_ID)

video_encoding_profiles = [
    dict(height=180, profile=ProfileH264.BASELINE, level=None, mode=StreamMode.PER_TITLE_TEMPLATE, aqs=1.2),
    dict(height=360, profile=ProfileH264.MAIN, level=None, mode=StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, min=300000, max=500000, aqs=1.2),
    dict(height=360, profile=ProfileH264.MAIN, level=None, mode=StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, min=600000, max=900000, aqs=1.2),
    dict(height=540, profile=ProfileH264.MAIN, level=None, mode=StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, min=1000000, max=1400000, aqs=1.2),
    dict(height=720, profile=ProfileH264.HIGH, level=None, mode=StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, min=1800000, max=2400000, aqs=1.0),
    dict(height=900, profile=ProfileH264.HIGH, level=None, mode=StreamMode.PER_TITLE_TEMPLATE, aqs=0.8),
    dict(height=1080, profile=ProfileH264.HIGH, level=None, mode=StreamMode.PER_TITLE_TEMPLATE, aqs=0.5),
]

audio_encoding_profiles = [
    dict(bitrate=128000, rate=48_000),
    dict(bitrate=64000, rate=44_100)
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
            name='Sample H264 Per-Title Encoding (Separate AV Inputs)',
            cloud_region=CloudRegion.AWS_AP_NORTHEAST_1,
            encoder_version='STABLE'))

    # === IngestInputStream definition for video and audio (separate files) ===
    # Video: extract video track from video-only mp4 file
    video_ingest_input_stream = bitmovin_api.encoding.encodings.input_streams.ingest.create(
        encoding_id=encoding.id,
        ingest_input_stream=IngestInputStream(
            input_id=s3_input.id,
            input_path=VIDEO_INPUT_PATH,
            selection_mode=StreamSelectionMode.VIDEO_RELATIVE,
            position=0))

    # Audio: extract audio track from audio-only wav file
    audio_ingest_input_stream = bitmovin_api.encoding.encodings.input_streams.ingest.create(
        encoding_id=encoding.id,
        ingest_input_stream=IngestInputStream(
            input_id=s3_input.id,
            input_path=AUDIO_INPUT_PATH,
            selection_mode=StreamSelectionMode.AUDIO_RELATIVE,
            position=0))

    # Create StreamInput references from IngestInputStreams
    video_input_stream = StreamInput(input_stream_id=video_ingest_input_stream.id)
    audio_input_stream = StreamInput(input_stream_id=audio_ingest_input_stream.id)

    # === Video Codec Configuration ===
    for video_profile in video_encoding_profiles:
        color_config = ColorConfig(copy_color_primaries_flag=True,
                                   copy_color_transfer_flag=True,
                                   copy_color_space_flag=True)

        h264_codec = bitmovin_api.encoding.configurations.video.h264.create(
            h264_video_configuration=H264VideoConfiguration(
                name='Sample video codec configuration',
                profile=video_profile.get("profile"),
                height=video_profile.get("height"),
                level=video_profile.get("level"),
                min_keyframe_interval=2,
                max_keyframe_interval=2,
                slices=1,
                trellis=H264Trellis.ENABLED_ALL,
                mv_search_range_max=24,
                rc_lookahead=60,
                sub_me=H264SubMe.RD_REF_IP,
                motion_estimation_method=H264MotionEstimationMethod.UMH,
                scene_cut_threshold=40,
                adaptive_quantization_mode=AdaptiveQuantMode.AUTO_VARIANCE_DARK_SCENES,
                adaptive_quantization_strength=video_profile.get('aqs'),
                mv_prediction_mode=MvPredictionMode.AUTO,
                psy_rate_distortion_optimization=0,
                psy_trellis=0,
                color_config=color_config
            )
        )

        if video_profile.get('mode') == StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE:
            h264_stream = bitmovin_api.encoding.encodings.streams.create(
                encoding_id=encoding.id,
                stream=Stream(
                    codec_config_id=h264_codec.id,
                    input_streams=[video_input_stream],
                    name="Stream H264 PerTitle",
                    mode=video_profile.get('mode'),
                    per_title_settings=StreamPerTitleSettings(
                        fixed_resolution_and_bitrate_settings=StreamPerTitleFixedResolutionAndBitrateSettings(
                            min_bitrate=video_profile.get('min'),
                            max_bitrate=video_profile.get('max'),
                            bitrate_selection_mode=BitrateSelectionMode.COMPLEXITY_RANGE,
                            low_complexity_boundary_for_max_bitrate=2160000,
                            high_complexity_boundary_for_max_bitrate=4000000
                        )
                    )
                )
            )
        else:
            h264_stream = bitmovin_api.encoding.encodings.streams.create(
                encoding_id=encoding.id,
                stream=Stream(
                    codec_config_id=h264_codec.id,
                    input_streams=[video_input_stream],
                    name="Stream H264 PerTitle",
                    mode=video_profile.get('mode')
                )
            )

        # Create Fmp4 muxing
        bitmovin_api.encoding.encodings.muxings.fmp4.create(
            encoding_id=encoding.id,
            fmp4_muxing=Fmp4Muxing(
                segment_length=6,
                segment_naming='segment_%number%.m4s',
                init_segment_name='init.mp4',
                streams=[MuxingStream(stream_id=h264_stream.id)],
                outputs=[EncodingOutput(
                    output_id=s3_output.id,
                    output_path=OUTPUT_BASE_PATH + "video/fmp4/{height}p_{bitrate}_{uuid}",
                    acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])
                ],
                name="Video FMP4 Muxing PerTitle"))

        # Create Ts muxing
        bitmovin_api.encoding.encodings.muxings.ts.create(
            encoding_id=encoding.id,
            ts_muxing=TsMuxing(
                segment_length=6,
                segment_naming='segment_%number%.ts',
                streams=[MuxingStream(stream_id=h264_stream.id)],
                outputs=[EncodingOutput(
                    output_id=s3_output.id,
                    output_path=OUTPUT_BASE_PATH + "video/ts/{height}p_{bitrate}_{uuid}",
                    acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])
                ],
                name="Video Ts Muxing PerTitle"))


    # === Audio Profile definition ===
    for audio_profile in audio_encoding_profiles:
        # Create Audio Codec Configuration
        aac_codec = bitmovin_api.encoding.configurations.audio.aac.create(
            aac_audio_configuration=AacAudioConfiguration(
                bitrate=audio_profile.get("bitrate"),
                rate=audio_profile.get("rate"),
                channel_layout=AacChannelLayout.CL_STEREO))

        # Create Audio Stream
        aac_stream = bitmovin_api.encoding.encodings.streams.create(
            encoding_id=encoding.id,
            stream=Stream(
                codec_config_id=aac_codec.id,
                input_streams=[audio_input_stream],
                name=f"Stream AAC {audio_profile.get('bitrate') / 1000:.0f}kbps",
                mode=StreamMode.STANDARD))

        # Create Fmp4 muxing
        bitmovin_api.encoding.encodings.muxings.fmp4.create(
            encoding_id=encoding.id,
            fmp4_muxing=Fmp4Muxing(
                segment_length=6,
                segment_naming='segment_%number%.m4s',
                init_segment_name='init.mp4',
                streams=[MuxingStream(stream_id=aac_stream.id)],
                outputs=[EncodingOutput(
                    output_id=s3_output.id,
                    output_path=f"{OUTPUT_BASE_PATH}audio/fmp4/{audio_profile.get('bitrate')}",
                    acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])],
                name=f"Audio FMP4 Muxing {audio_profile.get('bitrate') / 1000:.0f}kbps"))

        # Create Ts muxing
        bitmovin_api.encoding.encodings.muxings.ts.create(
            encoding_id=encoding.id,
            ts_muxing=TsMuxing(
                segment_length=6,
                segment_naming='segment_%number%.ts',
                streams=[MuxingStream(stream_id=aac_stream.id)],
                outputs=[EncodingOutput(
                    output_id=s3_output.id,
                    output_path=f"{OUTPUT_BASE_PATH}audio/ts/{audio_profile.get('bitrate')}",
                    acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])],
                name=f"Audio Ts Muxing {audio_profile.get('bitrate') / 1000:.0f}kbps"))

    # === Start Encoding ===
    start_encoding_request = StartEncodingRequest(
        encoding_mode=EncodingMode.THREE_PASS,
        per_title=PerTitle(
            h264_configuration=H264PerTitleConfiguration(
                min_bitrate=128000,
                max_bitrate=4000000,
                codec_min_bitrate_factor=0.8,
                codec_max_bitrate_factor=1.2,
                codec_bufsize_factor=2.0,
                target_quality_crf=17,
                complexity_factor=1.0,
                fixed_resolution_and_bitrate_configuration=PerTitleFixedResolutionAndBitrateConfiguration(
                    forced_rendition_above_highest_fixed_representation=1,
                    forced_rendition_above_highest_fixed_representation_factor=1.2,
                    forced_rendition_above_highest_fixed_representation_calculation_mode=PerTitleFixedResolutionAndBitrateConfigurationMode.LAST_CALCULATED_BITRATE
                ),
                max_bitrate_step_size=4.0
            )
        )
    )
    _execute_encoding(encoding=encoding, start_encoding_request=start_encoding_request)

    hls_manifest = _create_hls_manifest(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)
    dash_manifest = _create_dash_manifest(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)
    _execute_hls_manifest_generation(hls_manifest=hls_manifest)
    _execute_dash_manifest_generation(dash_manifest=dash_manifest)


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


    ts_muxings = bitmovin_api.encoding.encodings.muxings.ts.list(encoding_id=encoding_id)
    for muxing in ts_muxings.items:
        stream = bitmovin_api.encoding.encodings.streams.get(
            encoding_id=encoding_id, stream_id=muxing.streams[0].stream_id)

        if 'PER_TITLE_TEMPLATE' in stream.mode.value:
            continue

        codec = bitmovin_api.encoding.configurations.type.get(configuration_id=stream.codec_config_id)
        segment_path = _remove_output_base_path(muxing.outputs[0].output_path)

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
                    muxing_id=muxing.id))

    return hls_manifest


def _create_dash_manifest(encoding_id, output, output_path):
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

    video_adaptation_set = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.video.create(
        video_adaptation_set=VideoAdaptationSet(),
        manifest_id=dash_manifest.id,
        period_id=period.id)
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

        if codec.type == CodecConfigType.AAC:
            bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
                manifest_id=dash_manifest.id,
                period_id=period.id,
                adaptationset_id=audio_adaptation_set.id,
                dash_fmp4_representation=DashFmp4Representation(
                    encoding_id=encoding_id,
                    muxing_id=muxing.id,
                    type_=DashRepresentationType.TEMPLATE,
                    segment_path=segment_path))

        elif codec.type == CodecConfigType.H264:
            bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
                manifest_id=dash_manifest.id,
                period_id=period.id,
                adaptationset_id=video_adaptation_set.id,
                dash_fmp4_representation=DashFmp4Representation(
                    encoding_id=encoding_id,
                    muxing_id=muxing.id,
                    type_=DashRepresentationType.TEMPLATE,
                    segment_path=segment_path))

    return dash_manifest


def _execute_hls_manifest_generation(hls_manifest):
    bitmovin_api.encoding.manifests.hls.start(
        manifest_id=hls_manifest.id,
        start_manifest_request=StartManifestRequest(
            manifest_generator=ManifestGenerator.V2
        )
    )

    task = _wait_for_hls_manifest_to_finish(manifest_id=hls_manifest.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_hls_manifest_to_finish(manifest_id=hls_manifest.id)
    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("HLS Manifest Creation failed")

    print("HLS Manifest Creation finished successfully")


def _execute_dash_manifest_generation(dash_manifest):
    bitmovin_api.encoding.manifests.dash.start(
        manifest_id=dash_manifest.id,
        start_manifest_request=StartManifestRequest(
            manifest_generator=ManifestGenerator.V2
        )
    )

    task = _wait_for_dash_manifest_to_finish(manifest_id=dash_manifest.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_dash_manifest_to_finish(manifest_id=dash_manifest.id)
    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("DASH Manifest Creation failed")

    print("DASH Manifest Creation finished successfully")


def _wait_for_encoding_to_finish(encoding_id):
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
