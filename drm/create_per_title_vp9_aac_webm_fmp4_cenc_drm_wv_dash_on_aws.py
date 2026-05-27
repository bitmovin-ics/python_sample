import time

from bitmovin_api_sdk import BitmovinApi
from bitmovin_api_sdk import S3Input, S3Output
from bitmovin_api_sdk import Encoding, CloudRegion, EncodingMode
from bitmovin_api_sdk import EncodingOutput, AclEntry, AclPermission
from bitmovin_api_sdk import IngestInputStream, StreamSelectionMode
from bitmovin_api_sdk import Stream, StreamInput, MuxingStream, StreamMode
from bitmovin_api_sdk import Vp9VideoConfiguration, Vp9Quality, Vp9AqMode, Vp9ArnrType
from bitmovin_api_sdk import ColorConfig, CodecConfigType
from bitmovin_api_sdk import AacAudioConfiguration, AacChannelLayout
from bitmovin_api_sdk import Fmp4Muxing, WebmMuxing
from bitmovin_api_sdk import CencDrm, CencWidevine, IvSize
from bitmovin_api_sdk import ContentProtection
from bitmovin_api_sdk import Condition, ConditionOperator
from bitmovin_api_sdk import DashManifest, Period, VideoAdaptationSet, AudioAdaptationSet
from bitmovin_api_sdk import DashFmp4Representation, DashWebmRepresentation, DashRepresentationType, DashRepresentationTypeMode
from bitmovin_api_sdk import StreamPerTitleFixedResolutionAndBitrateSettings, BitrateSelectionMode
from bitmovin_api_sdk import PerTitle, PerTitleFixedResolutionAndBitrateConfiguration
from bitmovin_api_sdk import PerTitleFixedResolutionAndBitrateConfigurationMode
from bitmovin_api_sdk import StreamPerTitleSettings, Vp9PerTitleConfiguration
from bitmovin_api_sdk import MessageType, StartEncodingRequest, StartManifestRequest, ManifestGenerator
from bitmovin_api_sdk import Status

TEST_ITEM = "per-title-vp9-aac-webm-fmp4-cenc-drm-wv-dash-aws"

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

bitmovin_api = BitmovinApi(api_key=API_KEY, tenant_org_id=ORG_ID)

# Per-Title ladder. The actual rendition list is expanded by Bitmovin Per-Title at encoding time
# based on these templates (PER_TITLE_TEMPLATE / PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE).
encoding_profiles_vp9_pertitle = [
    {"height": 180, "mode": StreamMode.PER_TITLE_TEMPLATE},
    {"height": 360, "mode": StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, "min": 210_000, "max": 350_000},
    {"height": 360, "mode": StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, "min": 420_000, "max": 630_000},
    {"height": 540, "mode": StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, "min": 700_000, "max": 980_000},
    {"height": 720, "mode": StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, "min": 1_250_000, "max": 1_700_000},
    {"height": 900, "mode": StreamMode.PER_TITLE_TEMPLATE},
    {"height": 1080, "mode": StreamMode.PER_TITLE_TEMPLATE},
]


def _vp9_cpu_and_tile_columns(height):
    """Hulu-recommended VP9 cpu_used / tile_columns by output height."""
    if height <= 240:
        return 1, 0
    if height <= 480:
        return 1, 1
    if height <= 1080:
        return 2, 2
    if height <= 1440:
        return 2, 3
    return 2, 4


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

    # === DRM CENC keys (Widevine only, IV size 8 bytes / CTR mode) ===
    widevine_drm = CencWidevine(pssh=CENC_WIDEVINE_PSSH)

    # === Video Profile definition (Per-Title with Hulu VP9 codec tuning) ===
    for profile_vp9 in encoding_profiles_vp9_pertitle:
        cpu_used, tile_columns = _vp9_cpu_and_tile_columns(profile_vp9.get("height"))

        color_config = ColorConfig(
            copy_color_primaries_flag=True,
            copy_color_transfer_flag=True,
            copy_color_space_flag=True,
            copy_chroma_location_flag=True,
            copy_color_range_flag=True)

        vp9_codec = bitmovin_api.encoding.configurations.video.vp9.create(
            vp9_video_configuration=Vp9VideoConfiguration(
                name='Sample video codec configuration',
                height=profile_vp9.get("height"),
                bitrate=None,
                rate=None,
                cpu_used=cpu_used,
                tile_columns=tile_columns,
                qp_min=0,
                qp_max=63,
                rate_undershoot_pct=25,
                rate_overshoot_pct=25,
                quality=Vp9Quality.GOOD,
                lossless=None,
                aq_mode=Vp9AqMode.NONE,
                arnr_type=Vp9ArnrType.CENTERED,
                arnr_max_frames=0,
                arnr_strength=3,
                color_config=color_config))

        # Create Video Stream (Per-Title template — fixed-resolution-and-bitrate variant carries extra settings)
        if profile_vp9.get('mode') == StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE:
            per_title_settings = StreamPerTitleSettings(
                fixed_resolution_and_bitrate_settings=StreamPerTitleFixedResolutionAndBitrateSettings(
                    min_bitrate=profile_vp9.get('min'),
                    max_bitrate=profile_vp9.get('max'),
                    bitrate_selection_mode=BitrateSelectionMode.COMPLEXITY_RANGE,
                    low_complexity_boundary_for_max_bitrate=1_500_000,
                    high_complexity_boundary_for_max_bitrate=3_200_000))
            vp9_stream = bitmovin_api.encoding.encodings.streams.create(
                encoding_id=encoding.id,
                stream=Stream(
                    codec_config_id=vp9_codec.id,
                    input_streams=[video_input_stream],
                    name=f"Stream VP9 {profile_vp9.get('height')}p",
                    mode=profile_vp9.get('mode'),
                    per_title_settings=per_title_settings))
        else:
            vp9_stream = bitmovin_api.encoding.encodings.streams.create(
                encoding_id=encoding.id,
                stream=Stream(
                    codec_config_id=vp9_codec.id,
                    input_streams=[video_input_stream],
                    name=f"Stream VP9 {profile_vp9.get('height')}p",
                    mode=profile_vp9.get('mode')))

        # {height}p_{bitrate}_{uuid} placeholders are substituted by Per-Title at encoding time;
        # {uuid} guarantees uniqueness across renditions even when other placeholders collide.
        video_muxing_output = EncodingOutput(
            output_id=s3_output.id,
            output_path=OUTPUT_BASE_PATH + "video/{height}p_{bitrate}_{uuid}/",
            acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])

        webm_muxing = bitmovin_api.encoding.encodings.muxings.webm.create(
            encoding_id=encoding.id,
            webm_muxing=WebmMuxing(
                segment_length=6,
                segment_naming='seg_%number%.chk',
                init_segment_name='init.hdr',
                streams=[MuxingStream(stream_id=vp9_stream.id)],
                name=f"Video WebM Muxing {profile_vp9.get('height')}p"))

        bitmovin_api.encoding.encodings.muxings.webm.drm.cenc.create(
            encoding_id=encoding.id,
            muxing_id=webm_muxing.id,
            cenc_drm=CencDrm(
                key=CENC_KEY,
                kid=CENC_KID,
                widevine=widevine_drm,
                outputs=[video_muxing_output],
                name="Video WebM CENC",
                iv_size=IvSize.IV_8_BYTES))

    # === Audio Profile definition (AAC in FMP4 sidecar; WebM video pairs with FMP4 audio in DASH) ===
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
            outputs=[audio_muxing_output],
            name='Audio FMP4 CENC',
            iv_size=IvSize.IV_8_BYTES))

    # === Per-Title configuration ===
    per_title = PerTitle(
        vp9_configuration=Vp9PerTitleConfiguration(
            min_bitrate=128_000,
            max_bitrate=3_200_000,
            target_quality_crf=18,
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

    # === Create + generate DASH manifest ===
    dash_manifest = _create_dash_manifest(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)
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

    # Audio is in FMP4 (sidecar), video Per-Title renditions are in WebM. Iterate both containers.
    fmp4_muxings = bitmovin_api.encoding.encodings.muxings.fmp4.list(encoding_id=encoding_id)
    for muxing in fmp4_muxings.items:
        stream = bitmovin_api.encoding.encodings.streams.get(
            encoding_id=encoding_id, stream_id=muxing.streams[0].stream_id)

        if 'PER_TITLE_TEMPLATE' in stream.mode.value:
            continue

        codec = bitmovin_api.encoding.configurations.type.get(configuration_id=stream.codec_config_id)
        if codec.type != CodecConfigType.AAC:
            continue

        drm = bitmovin_api.encoding.encodings.muxings.fmp4.drm.cenc.list(
            encoding_id=encoding_id, muxing_id=muxing.id).items
        if not drm:
            continue
        segment_path = _remove_output_base_path(drm[0].outputs[0].output_path)

        representation = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
            manifest_id=dash_manifest.id,
            period_id=period.id,
            adaptationset_id=audio_adaptation_set.id,
            dash_fmp4_representation=DashFmp4Representation(
                encoding_id=encoding_id,
                muxing_id=muxing.id,
                type_=DashRepresentationType.TEMPLATE,
                mode=DashRepresentationTypeMode.TEMPLATE_REPRESENTATION,
                segment_path=segment_path))
        bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.contentprotection.create(
            manifest_id=dash_manifest.id,
            period_id=period.id,
            adaptationset_id=audio_adaptation_set.id,
            representation_id=representation.id,
            content_protection=ContentProtection(
                encoding_id=encoding_id,
                muxing_id=muxing.id,
                drm_id=drm[0].id))

    webm_muxings = bitmovin_api.encoding.encodings.muxings.webm.list(encoding_id=encoding_id)
    for muxing in webm_muxings.items:
        stream = bitmovin_api.encoding.encodings.streams.get(
            encoding_id=encoding_id, stream_id=muxing.streams[0].stream_id)

        if 'PER_TITLE_TEMPLATE' in stream.mode.value:
            continue

        drm = bitmovin_api.encoding.encodings.muxings.webm.drm.cenc.list(
            encoding_id=encoding_id, muxing_id=muxing.id).items
        if not drm:
            continue
        segment_path = _remove_output_base_path(drm[0].outputs[0].output_path)

        representation = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.webm.create(
            manifest_id=dash_manifest.id,
            period_id=period.id,
            adaptationset_id=video_adaptation_set.id,
            dash_webm_representation=DashWebmRepresentation(
                encoding_id=encoding_id,
                muxing_id=muxing.id,
                type_=DashRepresentationType.TEMPLATE,
                segment_path=segment_path))
        bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.webm.contentprotection.create(
            manifest_id=dash_manifest.id,
            period_id=period.id,
            adaptationset_id=video_adaptation_set.id,
            representation_id=representation.id,
            content_protection=ContentProtection(
                encoding_id=encoding_id,
                muxing_id=muxing.id,
                drm_id=drm[0].id))

    return dash_manifest


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
