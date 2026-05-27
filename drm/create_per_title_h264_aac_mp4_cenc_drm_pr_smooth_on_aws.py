import time

from bitmovin_api_sdk import BitmovinApi
from bitmovin_api_sdk import S3Input, S3Output
from bitmovin_api_sdk import Encoding, CloudRegion, EncodingMode
from bitmovin_api_sdk import EncodingOutput, AclEntry, AclPermission
from bitmovin_api_sdk import IngestInputStream, StreamSelectionMode
from bitmovin_api_sdk import Stream, StreamInput, MuxingStream, StreamMode
from bitmovin_api_sdk import H264VideoConfiguration, ProfileH264
from bitmovin_api_sdk import H264MotionEstimationMethod, MvPredictionMode, AdaptiveQuantMode
from bitmovin_api_sdk import ColorConfig, CodecConfigType, H264Trellis, H264SubMe
from bitmovin_api_sdk import AacAudioConfiguration, AacChannelLayout
from bitmovin_api_sdk import Mp4Muxing, FragmentedMp4MuxingManifestType
from bitmovin_api_sdk import CencDrm, CencPlayReady, IvSize
from bitmovin_api_sdk import Condition, ConditionOperator
from bitmovin_api_sdk import SmoothStreamingManifest, SmoothStreamingRepresentation
from bitmovin_api_sdk import SmoothManifestContentProtection
from bitmovin_api_sdk import StreamPerTitleFixedResolutionAndBitrateSettings, BitrateSelectionMode
from bitmovin_api_sdk import PerTitle, PerTitleFixedResolutionAndBitrateConfiguration
from bitmovin_api_sdk import PerTitleFixedResolutionAndBitrateConfigurationMode
from bitmovin_api_sdk import StreamPerTitleSettings, H264PerTitleConfiguration
from bitmovin_api_sdk import MessageType, StartEncodingRequest, StartManifestRequest, ManifestGenerator
from bitmovin_api_sdk import Status

TEST_ITEM = "per-title-h264-aac-mp4-cenc-drm-pr-smooth-aws"

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
CENC_KID = '43215678123412341234123412341234'
CENC_PLAYREADY_LA_URL = 'http://pr.test.expressplay.com/playready/RightsManager.asmx'

bitmovin_api = BitmovinApi(api_key=API_KEY, tenant_org_id=ORG_ID)

# Per-Title ladder. The actual rendition list is expanded by Bitmovin Per-Title at encoding time
# based on these templates (PER_TITLE_TEMPLATE / PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE).
encoding_profiles_h264_pertitle = [
    {"height": 180, "profile": ProfileH264.BASELINE, "level": None, "mode": StreamMode.PER_TITLE_TEMPLATE, "aqs": 1.2},
    {"height": 360, "profile": ProfileH264.MAIN, "level": None, "mode": StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, "min": 300_000, "max": 500_000, "aqs": 1.2},
    {"height": 360, "profile": ProfileH264.MAIN, "level": None, "mode": StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, "min": 600_000, "max": 900_000, "aqs": 1.2},
    {"height": 540, "profile": ProfileH264.MAIN, "level": None, "mode": StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, "min": 1_000_000, "max": 1_400_000, "aqs": 1.2},
    {"height": 720, "profile": ProfileH264.HIGH, "level": None, "mode": StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, "min": 1_800_000, "max": 2_400_000, "aqs": 1.0},
    {"height": 900, "profile": ProfileH264.HIGH, "level": None, "mode": StreamMode.PER_TITLE_TEMPLATE, "aqs": 0.8},
    {"height": 1080, "profile": ProfileH264.HIGH, "level": None, "mode": StreamMode.PER_TITLE_TEMPLATE, "aqs": 0.5},
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

    # === DRM CENC keys (PlayReady only, IV size 8 bytes / CTR mode) ===
    playready_drm = CencPlayReady(la_url=CENC_PLAYREADY_LA_URL)

    # === Video Profile definition (Per-Title with Hulu codec tuning) ===
    for profile_h264 in encoding_profiles_h264_pertitle:
        color_config = ColorConfig(
            copy_color_primaries_flag=True,
            copy_color_transfer_flag=True,
            copy_color_space_flag=True)

        h264_codec = bitmovin_api.encoding.configurations.video.h264.create(
            h264_video_configuration=H264VideoConfiguration(
                name='Sample video codec configuration',
                profile=profile_h264.get("profile"),
                height=profile_h264.get("height"),
                level=profile_h264.get("level"),
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
                adaptive_quantization_strength=profile_h264.get('aqs'),
                mv_prediction_mode=MvPredictionMode.AUTO,
                psy_rate_distortion_optimization=0,
                psy_trellis=0,
                color_config=color_config))

        # Create Video Stream (Per-Title template — fixed-resolution-and-bitrate variant carries extra settings)
        if profile_h264.get('mode') == StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE:
            per_title_settings = StreamPerTitleSettings(
                fixed_resolution_and_bitrate_settings=StreamPerTitleFixedResolutionAndBitrateSettings(
                    min_bitrate=profile_h264.get('min'),
                    max_bitrate=profile_h264.get('max'),
                    bitrate_selection_mode=BitrateSelectionMode.COMPLEXITY_RANGE,
                    low_complexity_boundary_for_max_bitrate=2_160_000,
                    high_complexity_boundary_for_max_bitrate=4_000_000))
            h264_stream = bitmovin_api.encoding.encodings.streams.create(
                encoding_id=encoding.id,
                stream=Stream(
                    codec_config_id=h264_codec.id,
                    input_streams=[video_input_stream],
                    name=f"Stream H264 {profile_h264.get('height')}p",
                    mode=profile_h264.get('mode'),
                    per_title_settings=per_title_settings))
        else:
            h264_stream = bitmovin_api.encoding.encodings.streams.create(
                encoding_id=encoding.id,
                stream=Stream(
                    codec_config_id=h264_codec.id,
                    input_streams=[video_input_stream],
                    name=f"Stream H264 {profile_h264.get('height')}p",
                    mode=profile_h264.get('mode')))

        # {height}p_{bitrate}_{uuid} placeholders are substituted by Per-Title at encoding time;
        # {uuid} guarantees uniqueness across renditions even when other placeholders collide.
        video_muxing_output = EncodingOutput(
            output_id=s3_output.id,
            output_path=OUTPUT_BASE_PATH + "video/{height}p_{bitrate}_{uuid}/",
            acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])

        # Fragmented MP4 (ismv) for Smooth Streaming output.
        mp4_muxing = bitmovin_api.encoding.encodings.muxings.mp4.create(
            encoding_id=encoding.id,
            mp4_muxing=Mp4Muxing(
                filename="video.ismv",
                fragment_duration=6000,
                fragmented_mp4_muxing_manifest_type=FragmentedMp4MuxingManifestType.SMOOTH,
                streams=[MuxingStream(stream_id=h264_stream.id)],
                name=f"Video MP4 Muxing {profile_h264.get('height')}p"))

        bitmovin_api.encoding.encodings.muxings.mp4.drm.cenc.create(
            encoding_id=encoding.id,
            muxing_id=mp4_muxing.id,
            cenc_drm=CencDrm(
                key=CENC_KEY,
                kid=CENC_KID,
                play_ready=playready_drm,
                outputs=[video_muxing_output],
                name="Video MP4 CENC PlayReady",
                iv_size=IvSize.IV_8_BYTES))

    # === Audio Profile definition ===
    aac_codec = bitmovin_api.encoding.configurations.audio.aac.create(
        aac_audio_configuration=AacAudioConfiguration(
            name='AAC Codec Configuration',
            bitrate=128_000,
            rate=48_000,
            channel_layout=AacChannelLayout.CL_STEREO))

    aac_stream = bitmovin_api.encoding.encodings.streams.create(
        encoding_id=encoding.id,
        stream=Stream(
            codec_config_id=aac_codec.id,
            input_streams=[audio_input_stream],
            name='Stream AAC 128kbps',
            conditions=Condition(
                attribute="AUDIOSTREAMCOUNT",
                operator=ConditionOperator.GREATER_THAN,
                value="0"),
            mode=StreamMode.STANDARD))

    audio_muxing_output = EncodingOutput(
        output_id=s3_output.id,
        output_path=f"{OUTPUT_BASE_PATH}audio/",
        acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])

    audio_mp4_muxing = bitmovin_api.encoding.encodings.muxings.mp4.create(
        encoding_id=encoding.id,
        mp4_muxing=Mp4Muxing(
            filename="audio.isma",
            fragment_duration=6000,
            fragmented_mp4_muxing_manifest_type=FragmentedMp4MuxingManifestType.SMOOTH,
            streams=[MuxingStream(stream_id=aac_stream.id)],
            name='Audio MP4 Muxing'))

    bitmovin_api.encoding.encodings.muxings.mp4.drm.cenc.create(
        encoding_id=encoding.id,
        muxing_id=audio_mp4_muxing.id,
        cenc_drm=CencDrm(
            key=CENC_KEY,
            kid=CENC_KID,
            play_ready=playready_drm,
            outputs=[audio_muxing_output],
            name='Audio MP4 CENC PlayReady',
            iv_size=IvSize.IV_8_BYTES))

    # === Per-Title configuration ===
    per_title = PerTitle(
        h264_configuration=H264PerTitleConfiguration(
            min_bitrate=128_000,
            max_bitrate=4_000_000,
            codec_min_bitrate_factor=0.8,
            codec_max_bitrate_factor=1.2,
            codec_bufsize_factor=2.0,
            target_quality_crf=17,
            complexity_factor=1.0,
            max_bitrate_step_size=4.0,
            fixed_resolution_and_bitrate_configuration=PerTitleFixedResolutionAndBitrateConfiguration(
                forced_rendition_above_highest_fixed_representation=1,
                forced_rendition_above_highest_fixed_representation_factor=1.2,
                forced_rendition_above_highest_fixed_representation_calculation_mode=PerTitleFixedResolutionAndBitrateConfigurationMode.LAST_CALCULATED_BITRATE)))

    # === Start Encoding (manifests are generated post-encoding once Per-Title renditions are known) ===
    start_encoding_request = StartEncodingRequest(
        per_title=per_title,
        encoding_mode=EncodingMode.THREE_PASS)
    _execute_encoding(encoding=encoding, start_encoding_request=start_encoding_request)

    # === Create + generate Smooth Streaming manifest ===
    smooth_manifest = _create_smooth_manifest(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)
    _execute_smooth_manifest_generation(smooth_manifest=smooth_manifest)


def _execute_encoding(encoding, start_encoding_request):
    bitmovin_api.encoding.encodings.start(encoding_id=encoding.id, start_encoding_request=start_encoding_request)

    task = _wait_for_encoding_to_finish(encoding_id=encoding.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_encoding_to_finish(encoding_id=encoding.id)

    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("Encoding failed")

    print("Encoding finished successfully")


def _create_smooth_manifest(encoding_id, output, output_path):
    manifest_output = EncodingOutput(
        output_id=output.id,
        output_path=output_path,
        acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])

    smooth_manifest = bitmovin_api.encoding.manifests.smooth.create(
        smooth_streaming_manifest=SmoothStreamingManifest(
            outputs=[manifest_output],
            name='Smooth Manifest',
            server_manifest_name="stream.ism",
            client_manifest_name="stream.ismc"))

    # Iterate all non-template MP4 muxings (audio + Per-Title video renditions expanded by the encoder)
    # and add each as a Smooth Streaming representation with its CENC PlayReady content protection.
    mp4_muxings = bitmovin_api.encoding.encodings.muxings.mp4.list(encoding_id=encoding_id)
    for muxing in mp4_muxings.items:
        stream = bitmovin_api.encoding.encodings.streams.get(
            encoding_id=encoding_id, stream_id=muxing.streams[0].stream_id)

        if 'PER_TITLE_TEMPLATE' in stream.mode.value:
            continue

        codec = bitmovin_api.encoding.configurations.type.get(configuration_id=stream.codec_config_id)
        if codec.type == CodecConfigType.AAC:
            track_name = "audio"
        elif codec.type == CodecConfigType.H264:
            track_name = "video"
        else:
            continue

        drm = bitmovin_api.encoding.encodings.muxings.mp4.drm.cenc.list(
            encoding_id=encoding_id, muxing_id=muxing.id).items
        if not drm:
            continue
        segment_path = _remove_output_base_path(drm[0].outputs[0].output_path)

        bitmovin_api.encoding.manifests.smooth.representations.mp4.create(
            manifest_id=smooth_manifest.id,
            smooth_streaming_representation=SmoothStreamingRepresentation(
                encoding_id=encoding_id,
                muxing_id=muxing.id,
                media_file=segment_path + muxing.filename,
                language="en",
                track_name=track_name))
        bitmovin_api.encoding.manifests.smooth.contentprotection.create(
            manifest_id=smooth_manifest.id,
            smooth_manifest_content_protection=SmoothManifestContentProtection(
                encoding_id=encoding_id,
                muxing_id=muxing.id,
                drm_id=drm[0].id))

    return smooth_manifest


def _execute_smooth_manifest_generation(smooth_manifest):
    bitmovin_api.encoding.manifests.smooth.start(
        manifest_id=smooth_manifest.id,
        start_manifest_request=StartManifestRequest(manifest_generator=ManifestGenerator.V2))

    task = _wait_for_smooth_manifest_to_finish(manifest_id=smooth_manifest.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_smooth_manifest_to_finish(manifest_id=smooth_manifest.id)
    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("Smooth Manifest Creation failed")

    print("Smooth Manifest Creation finished successfully")


def _wait_for_encoding_to_finish(encoding_id):
    time.sleep(5)
    task = bitmovin_api.encoding.encodings.status(encoding_id=encoding_id)
    print(f"Encoding status is {task.status} (progress: {task.progress} %)")
    return task


def _wait_for_smooth_manifest_to_finish(manifest_id):
    time.sleep(5)
    task = bitmovin_api.encoding.manifests.smooth.status(manifest_id=manifest_id)
    print(f"Smooth manifest status is {task.status} (progress: {task.progress} %)")
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
