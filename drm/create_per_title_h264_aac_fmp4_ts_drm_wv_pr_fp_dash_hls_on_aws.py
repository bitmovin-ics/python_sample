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
from bitmovin_api_sdk import Fmp4Muxing, TsMuxing
from bitmovin_api_sdk import CencDrm, CencWidevine, CencPlayReady, IvSize
from bitmovin_api_sdk import FairPlayDrm
from bitmovin_api_sdk import ContentProtection
from bitmovin_api_sdk import Condition, ConditionOperator
from bitmovin_api_sdk import DashManifest, Period, VideoAdaptationSet, AudioAdaptationSet
from bitmovin_api_sdk import DashFmp4Representation, DashRepresentationType, DashRepresentationTypeMode
from bitmovin_api_sdk import HlsManifest, HlsVersion, AudioMediaInfo, StreamInfo
from bitmovin_api_sdk import StreamPerTitleFixedResolutionAndBitrateSettings, BitrateSelectionMode
from bitmovin_api_sdk import PerTitle, PerTitleFixedResolutionAndBitrateConfiguration
from bitmovin_api_sdk import PerTitleFixedResolutionAndBitrateConfigurationMode
from bitmovin_api_sdk import StreamPerTitleSettings, H264PerTitleConfiguration
from bitmovin_api_sdk import MessageType, StartEncodingRequest, StartManifestRequest, ManifestGenerator
from bitmovin_api_sdk import Status

TEST_ITEM = "per-title-h264-aac-fmp4-ts-drm-wv-pr-fp-dash-hls-aws"

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
CENC_WIDEVINE_PSSH = 'CAESEAABAgMEBQYHCAkKCwwNDg8aCmludGVydHJ1c3QiASo='
CENC_PLAYREADY_LA_URL = 'http://pr.test.expressplay.com/playready/RightsManager.asmx'

FAIRPLAY_KEY = '12341234123412341234123412341234'
FAIRPLAY_IV = '00000000000000000000000000000000'
FAIRPLAY_URI = 'skd://expressplay_token'

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

    # === DRM keys ===
    # DASH path uses CENC (Widevine + PlayReady, IV size 8 bytes / CTR mode) on FMP4 muxings.
    # HLS path uses standalone FairPlay (AES-CBC) on TS muxings.
    widevine_drm = CencWidevine(pssh=CENC_WIDEVINE_PSSH)
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

        # --- DASH leg: FMP4 muxing + CENC DRM ---
        # {uuid} is required for Per-Title to keep each rendition's output path unique.
        fmp4_video_output = EncodingOutput(
            output_id=s3_output.id,
            output_path=OUTPUT_BASE_PATH + "video/dash/{height}p_{bitrate}_{uuid}/",
            acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])

        fmp4_muxing = bitmovin_api.encoding.encodings.muxings.fmp4.create(
            encoding_id=encoding.id,
            fmp4_muxing=Fmp4Muxing(
                segment_length=6,
                segment_naming='seg_%number%.m4s',
                init_segment_name='init.mp4',
                streams=[MuxingStream(stream_id=h264_stream.id)],
                name=f"Video FMP4 Muxing {profile_h264.get('height')}p"))

        bitmovin_api.encoding.encodings.muxings.fmp4.drm.cenc.create(
            encoding_id=encoding.id,
            muxing_id=fmp4_muxing.id,
            cenc_drm=CencDrm(
                key=CENC_KEY,
                kid=CENC_KID,
                widevine=widevine_drm,
                play_ready=playready_drm,
                outputs=[fmp4_video_output],
                name="Video FMP4 CENC",
                iv_size=IvSize.IV_8_BYTES))

        # --- HLS leg: TS muxing + FairPlay DRM ---
        ts_video_output = EncodingOutput(
            output_id=s3_output.id,
            output_path=OUTPUT_BASE_PATH + "video/hls/{height}p_{bitrate}_{uuid}/",
            acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])

        ts_muxing = bitmovin_api.encoding.encodings.muxings.ts.create(
            encoding_id=encoding.id,
            ts_muxing=TsMuxing(
                segment_length=6,
                segment_naming='seg_%number%.ts',
                streams=[MuxingStream(stream_id=h264_stream.id)],
                name=f"Video TS Muxing {profile_h264.get('height')}p"))

        bitmovin_api.encoding.encodings.muxings.ts.drm.fairplay.create(
            encoding_id=encoding.id,
            muxing_id=ts_muxing.id,
            fair_play_drm=FairPlayDrm(
                key=FAIRPLAY_KEY,
                iv=FAIRPLAY_IV,
                uri=FAIRPLAY_URI,
                outputs=[ts_video_output],
                name='Video TS FairPlay'))

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

    # --- Audio DASH leg: FMP4 muxing + CENC DRM ---
    fmp4_audio_output = EncodingOutput(
        output_id=s3_output.id,
        output_path=f"{OUTPUT_BASE_PATH}audio/dash/",
        acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])

    audio_fmp4_muxing = bitmovin_api.encoding.encodings.muxings.fmp4.create(
        encoding_id=encoding.id,
        fmp4_muxing=Fmp4Muxing(
            segment_length=6,
            segment_naming='seg_%number%.m4s',
            init_segment_name='init.mp4',
            streams=[MuxingStream(stream_id=aac_stream.id)],
            name='Audio FMP4 Muxing'))

    bitmovin_api.encoding.encodings.muxings.fmp4.drm.cenc.create(
        encoding_id=encoding.id,
        muxing_id=audio_fmp4_muxing.id,
        cenc_drm=CencDrm(
            key=CENC_KEY,
            kid=CENC_KID,
            widevine=widevine_drm,
            play_ready=playready_drm,
            outputs=[fmp4_audio_output],
            name='Audio FMP4 CENC',
            iv_size=IvSize.IV_8_BYTES))

    # --- Audio HLS leg: TS muxing + FairPlay DRM ---
    ts_audio_output = EncodingOutput(
        output_id=s3_output.id,
        output_path=f"{OUTPUT_BASE_PATH}audio/hls/",
        acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])

    audio_ts_muxing = bitmovin_api.encoding.encodings.muxings.ts.create(
        encoding_id=encoding.id,
        ts_muxing=TsMuxing(
            segment_length=6,
            segment_naming='seg_%number%.ts',
            streams=[MuxingStream(stream_id=aac_stream.id)],
            name='Audio TS Muxing'))

    bitmovin_api.encoding.encodings.muxings.ts.drm.fairplay.create(
        encoding_id=encoding.id,
        muxing_id=audio_ts_muxing.id,
        fair_play_drm=FairPlayDrm(
            key=FAIRPLAY_KEY,
            iv=FAIRPLAY_IV,
            uri=FAIRPLAY_URI,
            outputs=[ts_audio_output],
            name='Audio TS FairPlay'))

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

    # === Create + generate DASH and HLS manifests ===
    dash_manifest = _create_dash_manifest(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)
    hls_manifest = _create_hls_manifest(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)
    _execute_dash_manifest_generation(dash_manifest=dash_manifest)
    _execute_hls_manifest_generation(hls_manifest=hls_manifest)


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
    """DASH manifest. Adds one representation per non-template FMP4 muxing (audio + Per-Title video
    renditions expanded by the encoder), each routed to the matching adaptation set with its CENC DRM."""
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
        if codec.type == CodecConfigType.AAC:
            adaptationset_id = audio_adaptation_set.id
        elif codec.type == CodecConfigType.H264:
            adaptationset_id = video_adaptation_set.id
        else:
            continue

        drm = bitmovin_api.encoding.encodings.muxings.fmp4.drm.cenc.list(
            encoding_id=encoding_id, muxing_id=muxing.id).items
        if not drm:
            continue
        segment_path = _remove_output_base_path(drm[0].outputs[0].output_path)

        representation = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
            manifest_id=dash_manifest.id,
            period_id=period.id,
            adaptationset_id=adaptationset_id,
            dash_fmp4_representation=DashFmp4Representation(
                encoding_id=encoding_id,
                muxing_id=muxing.id,
                type_=DashRepresentationType.TEMPLATE,
                mode=DashRepresentationTypeMode.TEMPLATE_REPRESENTATION,
                segment_path=segment_path))
        bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.contentprotection.create(
            manifest_id=dash_manifest.id,
            period_id=period.id,
            adaptationset_id=adaptationset_id,
            representation_id=representation.id,
            content_protection=ContentProtection(
                encoding_id=encoding_id,
                muxing_id=muxing.id,
                drm_id=drm[0].id))

    return dash_manifest


def _create_hls_manifest(encoding_id, output, output_path):
    """HLS manifest. Adds one entry per non-template TS muxing (audio media + Per-Title video variant
    streams expanded by the encoder), each linked to its FairPlay DRM."""
    manifest_output = EncodingOutput(
        output_id=output.id,
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

        drm = bitmovin_api.encoding.encodings.muxings.ts.drm.fairplay.list(
            encoding_id=encoding_id, muxing_id=muxing.id).items
        if not drm:
            continue
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
            bitmovin_api.encoding.manifests.hls.streams.create(
                manifest_id=hls_manifest.id,
                stream_info=StreamInfo(
                    audio='audio',
                    closed_captions='NONE',
                    segment_path=segment_path,
                    uri=f'video_{muxing.avg_bitrate}.m3u8',
                    encoding_id=encoding_id,
                    stream_id=stream.id,
                    muxing_id=muxing.id,
                    drm_id=drm[0].id))

    return hls_manifest


def _execute_dash_manifest_generation(dash_manifest):
    bitmovin_api.encoding.manifests.dash.start(
        manifest_id=dash_manifest.id,
        start_manifest_request=StartManifestRequest(manifest_generator=ManifestGenerator.V2))

    task = _wait_for_dash_manifest_to_finish(manifest_id=dash_manifest.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_dash_manifest_to_finish(manifest_id=dash_manifest.id)
    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("DASH Manifest Creation failed")

    print("DASH Manifest Creation finished successfully")


def _execute_hls_manifest_generation(hls_manifest):
    bitmovin_api.encoding.manifests.hls.start(
        manifest_id=hls_manifest.id,
        start_manifest_request=StartManifestRequest(manifest_generator=ManifestGenerator.V2))

    task = _wait_for_hls_manifest_to_finish(manifest_id=hls_manifest.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_hls_manifest_to_finish(manifest_id=hls_manifest.id)
    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("HLS Manifest Creation failed")

    print("HLS Manifest Creation finished successfully")


def _wait_for_encoding_to_finish(encoding_id):
    time.sleep(5)
    task = bitmovin_api.encoding.encodings.status(encoding_id=encoding_id)
    print(f"Encoding status is {task.status} (progress: {task.progress} %)")
    return task


def _wait_for_dash_manifest_to_finish(manifest_id):
    time.sleep(5)
    task = bitmovin_api.encoding.manifests.dash.status(manifest_id=manifest_id)
    print(f"DASH manifest status is {task.status} (progress: {task.progress} %)")
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
