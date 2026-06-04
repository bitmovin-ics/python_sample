"""Dolby Vision input -> Dolby Vision / HDR10 / SDR (HLS + DASH) sample.

This sample delivers THREE viewing experiences from a single Dolby Vision mezzanine,
using TWO separate encodings and ONE combined HLS + DASH manifest pair.

WHY TWO ENCODINGS:
  Bitmovin rejects mixing dynamic range formats that are derived from the same Dolby
  Vision input *within a single encoding* (API error code 2065: "Combination of
  different Dolby Vision filters is currently not supported. It's not possible to mix
  Dolby Vision, SDR or HDR10 streams from the same Dolby Vision input streams in the
  same encoding."). So each dynamic range format gets its own encoding:

  1. DV encoding — Dolby Vision Profile 8.1 ladder
     (`H265DynamicRangeFormat.DOLBY_VISION_PROFILE_8_1`). Profile 8.1 is
     *cross-compatible*: each stream carries an HDR10-conformant base layer
     (BT.2020 / PQ / 10-bit + HDR10 static metadata) plus a Dolby Vision RPU.
       - Dolby Vision capable devices read the RPU and render Dolby Vision.
       - HDR10-only devices ignore the RPU and render the HDR10 base layer.
     So this single ladder serves both the "Dolby Vision" and the "HDR10" outputs;
     no separate HDR10 encode is required. Atmos + AAC audio live in this encoding.

  2. SDR encoding — SDR ladder (`H265DynamicRangeFormat.SDR`). The encoder performs
     HDR-to-SDR conversion (tone mapping) from the same Dolby Vision input, in its own
     encoding, so SDR-only devices get a correctly tone-mapped rendition.

MANIFESTS (generated AFTER both encodings finish, spanning muxings from both):
  Because the variants live in two encodings, the manifests cannot be produced by a
  single encoding's start request. Instead both encodings run to completion, then one
  HLS master and one DASH MPD are assembled — each representation / stream / audio-media
  entry references its owning encoding via encoding_id + muxing_id — and finalized with
  the V2 manifest generator (`manifests.{dash,hls}.start`).

  Per the Apple HLS Authoring Specification:
    - A single master playlist references every variant; variants are paired with both
      audio rendition groups (`aac` DEFAULT=YES, `atmos` AUTOSELECT=YES).
    - The V2 generator populates VIDEO-RANGE (PQ for the 8.1 ladder, SDR for the SDR
      ladder), CODECS and, for the Profile 8.1 variants, the SUPPLEMENTAL-CODECS
      attribute that lets HDR10-only players fall back to the HDR10 base layer. Inspect
      the generated playlist and confirm SUPPLEMENTAL-CODECS is present on the 8.1
      variants; if your encoder version does not emit it, HDR10-only devices would fall
      back to the SDR ladder instead.
    - Every video rendition gets an EXT-X-I-FRAME-STREAM-INF entry for trick-play.
"""

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
from bitmovin_api_sdk import MessageType, StartEncodingRequest, StartManifestRequest, ManifestGenerator
from bitmovin_api_sdk import Status

TEST_ITEM = "dolbyvision-hdr10-sdr-2ladder-profile81-hls-dash-fmp4"

API_KEY = '<INSERT YOUR API KEY>'
ORG_ID = '<INSERT YOUR ORG ID>'

S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

S3_OUTPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_OUTPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_OUTPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

# Dolby Vision video + sidecar metadata. The same Dolby Vision input feeds BOTH the
# Profile 8.1 (DV/HDR10) encoding and the tone-mapped SDR encoding (separate encodings).
# (Reference assets are available from Netflix Open Content: https://opencontent.netflix.com/ — Sol Levante)
DOLBY_VISION_INPUT_PATH = '<INSERT_DOLBY_VISION_VIDEO_PATH>'
DOLBY_VISION_INPUT_METADATA = '<INSERT_DOLBY_VISION_METADATA_PATH>'

# Dolby Atmos DAMF mezzanine
DOLBY_ATMOS_DAMF_PATH = '<INSERT_DOLBY_ATMOS_DAMF_PATH>'

# AAC stereo mezzanine (universal fallback per HLS Authoring Spec)
AAC_2_0_INPUT_PATH = '<INSERT_AAC_2_0_MEZZANINE_PATH>'

OUTPUT_BASE_PATH = f'output/{TEST_ITEM}/'

bitmovin_api = BitmovinApi(api_key=API_KEY, tenant_org_id=ORG_ID)

# Dolby Vision Profile 8.1 ladder — one stream serves both DV and HDR10 devices.
# Lives in its own encoding (see module docstring / API code 2065).
encoding_profiles_video_dv = [
    {"drf": H265DynamicRangeFormat.DOLBY_VISION_PROFILE_8_1, "label": "dv81", "height": 2160, "bitrate": 15_000_000, "aqs": 0.5},
    {"drf": H265DynamicRangeFormat.DOLBY_VISION_PROFILE_8_1, "label": "dv81", "height": 1080, "bitrate": 6_000_000, "aqs": 0.8},
    {"drf": H265DynamicRangeFormat.DOLBY_VISION_PROFILE_8_1, "label": "dv81", "height": 720, "bitrate": 3_000_000, "aqs": 1.0},
    {"drf": H265DynamicRangeFormat.DOLBY_VISION_PROFILE_8_1, "label": "dv81", "height": 540, "bitrate": 1_800_000, "aqs": 1.2},
]

# SDR ladder — HDR-to-SDR tone mapping from the Dolby Vision input. Lives in its own encoding.
encoding_profiles_video_sdr = [
    {"drf": H265DynamicRangeFormat.SDR, "label": "sdr", "height": 2160, "bitrate": 12_000_000, "aqs": 0.5},
    {"drf": H265DynamicRangeFormat.SDR, "label": "sdr", "height": 1080, "bitrate": 5_000_000, "aqs": 0.8},
    {"drf": H265DynamicRangeFormat.SDR, "label": "sdr", "height": 720, "bitrate": 2_500_000, "aqs": 1.0},
    {"drf": H265DynamicRangeFormat.SDR, "label": "sdr", "height": 540, "bitrate": 1_500_000, "aqs": 1.2},
]

# Audio renditions: Atmos premium + AAC stereo universal fallback. Encoded once, in the
# DV encoding; the manifests pair every video variant (DV and SDR) with both audio groups.
encoding_profiles_audio = [
    {"codec": "atmos", "bitrate": 448_000, "rate": 48_000},
    {"codec": "aac", "bitrate": 128_000, "rate": 48_000, "channel_layout": AacChannelLayout.CL_STEREO},
]


def main():
    # === Input and Output definition (shared by both encodings) ===
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

    # === One encoding per dynamic range format ===
    # Mixing DV / HDR10 / SDR filters derived from the same Dolby Vision input inside a
    # single encoding is rejected (API code 2065), so DV 8.1 and SDR are split apart.
    encoding_dv = _create_dv_encoding(s3_input=s3_input, s3_output=s3_output)
    encoding_sdr = _create_sdr_encoding(s3_input=s3_input, s3_output=s3_output)

    # Start both encodings (no manifests here — they are generated afterwards across both
    # encodings), then wait for them concurrently and fail fast (stop the other) if either errors.
    # An exception during start must not leave an already-started encoding running either.
    encodings = [encoding_dv, encoding_sdr]
    started_ids = []
    try:
        for encoding in encodings:
            _start_encoding(encoding)
            started_ids.append(encoding.id)
    except BaseException:
        _stop_encodings(started_ids)
        raise
    _await_all_encodings(encodings)

    # === Build + generate one combined HLS master and one combined DASH MPD ===
    encoding_ids = [encoding_dv.id, encoding_sdr.id]
    dash_manifest = _create_dash_manifest(output=s3_output, output_path=OUTPUT_BASE_PATH, encoding_ids=encoding_ids)
    hls_manifest = _create_hls_manifest(output=s3_output, output_path=OUTPUT_BASE_PATH, encoding_ids=encoding_ids)
    _execute_dash_manifest_generation(dash_manifest=dash_manifest)
    _execute_hls_manifest_generation(hls_manifest=hls_manifest)


def _create_dv_encoding(s3_input, s3_output):
    """Encoding holding the Dolby Vision Profile 8.1 video ladder (DV + HDR10) and the
    Atmos + AAC audio renditions."""
    encoding = bitmovin_api.encoding.encodings.create(
        encoding=Encoding(
            name=f'{TEST_ITEM}-dv81',
            cloud_region=CloudRegion.AWS_AP_NORTHEAST_1,
            encoder_version='STABLE'))

    # DolbyVisionInputStream — the encoder derives the DV 8.1 renditions (with their HDR10
    # base layer) from this input.
    dv_video_ingest = bitmovin_api.encoding.encodings.input_streams.dolby_vision.create(
        encoding_id=encoding.id,
        dolby_vision_input_stream=DolbyVisionInputStream(
            input_id=s3_input.id,
            video_input_path=DOLBY_VISION_INPUT_PATH,
            metadata_input_path=DOLBY_VISION_INPUT_METADATA))
    video_input_stream = StreamInput(input_stream_id=dv_video_ingest.id)

    _add_h265_video_ladder(encoding, video_input_stream, encoding_profiles_video_dv, s3_output)
    _add_audio(encoding, s3_input, s3_output)
    return encoding


def _create_sdr_encoding(s3_input, s3_output):
    """Encoding holding the SDR video ladder, tone-mapped (HDR-to-SDR conversion) from the
    same Dolby Vision input. Separate encoding so it does not mix dynamic range formats
    with the DV 8.1 streams (API code 2065)."""
    encoding = bitmovin_api.encoding.encodings.create(
        encoding=Encoding(
            name=f'{TEST_ITEM}-sdr',
            cloud_region=CloudRegion.AWS_AP_NORTHEAST_1,
            encoder_version='STABLE'))

    # Same Dolby Vision input — DRF=SDR on the H265 configs triggers HDR-to-SDR tone mapping.
    dv_video_ingest = bitmovin_api.encoding.encodings.input_streams.dolby_vision.create(
        encoding_id=encoding.id,
        dolby_vision_input_stream=DolbyVisionInputStream(
            input_id=s3_input.id,
            video_input_path=DOLBY_VISION_INPUT_PATH,
            metadata_input_path=DOLBY_VISION_INPUT_METADATA))
    video_input_stream = StreamInput(input_stream_id=dv_video_ingest.id)

    _add_h265_video_ladder(encoding, video_input_stream, encoding_profiles_video_sdr, s3_output)
    return encoding


def _add_h265_video_ladder(encoding, video_input_stream, profiles, s3_output):
    """Create the H.265 codec config + stream + fMP4 muxing for each rendition in `profiles`.
    All profiles passed in share a single dynamic range format (one encoding == one DR)."""
    for profile in profiles:
        h265_codec = bitmovin_api.encoding.configurations.video.h265.create(
            h265_video_configuration=H265VideoConfiguration(
                name=f"H265 {profile['label'].upper()} {profile['height']}p",
                height=profile["height"],
                bitrate=profile["bitrate"],
                max_bitrate=profile["bitrate"] * 2,
                bufsize=profile["bitrate"] * 4,
                # Profile 8.1 keeps the stream HDR10-compatible; SDR triggers HDR-to-SDR conversion.
                dynamic_range_format=profile["drf"],
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
                name=f"Stream H265 {profile['label'].upper()} {profile['height']}p",
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
                    output_path=f"{OUTPUT_BASE_PATH}video/{profile['label']}/{profile['height']}p_{profile['bitrate']}/",
                    acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])],
                name=f"Video FMP4 {profile['label'].upper()} {profile['height']}p"))


def _add_audio(encoding, s3_input, s3_output):
    """Create the Atmos (DAMF) + AAC stereo audio codec configs + streams + fMP4 muxings."""
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


def _start_encoding(encoding):
    # No manifests in the start request: the combined HLS/DASH manifests are generated
    # afterwards (they span muxings from both encodings).
    bitmovin_api.encoding.encodings.start(
        encoding_id=encoding.id, start_encoding_request=StartEncodingRequest())
    print(f"Encoding '{encoding.name}' started")


def _await_all_encodings(encodings):
    """Wait for several encodings that run concurrently. Each cycle polls EVERY still-running
    encoding (not one after another), so a failure is detected within one poll interval no
    matter how long the other encodings take. Fails fast: on the first non-success terminal
    state — or ANY exception while polling — the remaining encodings are stopped and the
    error is re-raised. Returns only once all encodings have finished successfully.

    Progress is printed as ONE compact line per poll cycle (short ladder labels, e.g.
    "dv81 RUNNING 5% | sdr RUNNING 18%"), and only when something changed since the last
    printed line — plus a heartbeat at most every 12 cycles (~1 min) so long quiet
    stretches still show the script is alive."""
    failed_states = (Status.ERROR, Status.TRANSFER_ERROR, Status.CANCELED)
    # Short ladder labels (encoding name minus the TEST_ITEM prefix), derived once up front.
    pending = {encoding.id: encoding.name.replace(f'{TEST_ITEM}-', '', 1) for encoding in encodings}
    last_line = None
    cycles_since_print = 0
    try:
        while pending:
            time.sleep(5)
            snapshot = []
            for encoding_id in list(pending.keys()):
                short_name = pending[encoding_id]
                task = bitmovin_api.encoding.encodings.status(encoding_id=encoding_id)
                snapshot.append(f"{short_name} {task.status.value} {task.progress or 0}%")
                if task.status is Status.FINISHED:
                    print(f"Encoding '{short_name}' finished successfully")
                    del pending[encoding_id]
                elif task.status in failed_states:
                    _log_task_errors(task=task)
                    # Already terminal — drop it so the cleanup below only stops the others.
                    del pending[encoding_id]
                    raise Exception(f"Encoding '{short_name}' ended with status {task.status.value}")
            line = " | ".join(snapshot)
            cycles_since_print += 1
            if line != last_line or cycles_since_print >= 12:
                print(f"Encodings: {line}")
                last_line = line
                cycles_since_print = 0
    except BaseException:
        # Fail fast: never leave sibling encodings running (and billing) after any failure —
        # terminal API status and polling exceptions alike. The original error is re-raised.
        _stop_encodings(list(pending.keys()))
        raise


def _stop_encodings(encoding_ids):
    """Best-effort stop of still-running encodings, used to fail fast when a sibling errors."""
    for encoding_id in encoding_ids:
        try:
            bitmovin_api.encoding.encodings.stop(encoding_id=encoding_id)
            print(f"Requested stop of encoding {encoding_id}")
        except Exception as error:  # cleanup must not mask the original failure
            print(f"Could not stop encoding {encoding_id}: {error}")


def _create_dash_manifest(output, output_path, encoding_ids):
    """DASH manifest spanning both encodings. Separate video AdaptationSets for the DV 8.1
    (PQ) and SDR ladders so players select the set matching their display, plus one
    AdaptationSet each for Atmos and AAC stereo audio. The V2 generator is expected to
    populate `Role main`, the DolbyVision/HDR10 SupplementalProperty descriptors on the 8.1
    set and the EC-3 JOC descriptors on the Atmos set; inspect the generated MPD and patch
    here if missing."""
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

    video_as_dv = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.video.create(
        video_adaptation_set=VideoAdaptationSet(),
        manifest_id=dash_manifest.id,
        period_id=period.id)
    video_as_sdr = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.video.create(
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

    for encoding_id in encoding_ids:
        fmp4_muxings = bitmovin_api.encoding.encodings.muxings.fmp4.list(encoding_id=encoding_id)
        for muxing in fmp4_muxings.items:
            stream = bitmovin_api.encoding.encodings.streams.get(
                encoding_id=encoding_id, stream_id=muxing.streams[0].stream_id)

            if 'PER_TITLE_TEMPLATE' in stream.mode.value:
                continue

            codec = bitmovin_api.encoding.configurations.type.get(configuration_id=stream.codec_config_id)
            segment_path = _remove_output_base_path(muxing.outputs[0].output_path)

            if codec.type == CodecConfigType.H265:
                video_codec = bitmovin_api.encoding.configurations.video.h265.get(configuration_id=stream.codec_config_id)
                # DV 8.1 and SDR share the H265 codec type, so route by dynamic range format.
                adaptationset_id = video_as_sdr.id if _is_sdr(video_codec) else video_as_dv.id
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


def _create_hls_manifest(output, output_path, encoding_ids):
    """HLS manifest spanning both encodings. Two audio groups (`aac` default + `atmos`
    premium); each video rendition from both ladders is exposed as TWO variants (paired with
    each audio group) plus one #EXT-X-I-FRAME-STREAM-INF entry for trick-play. The V2
    generator populates VIDEO-RANGE (PQ for the 8.1 ladder, SDR for the SDR ladder), CODECS,
    CHANNELS and — for the 8.1 variants — SUPPLEMENTAL-CODECS so HDR10-only players fall back
    to the HDR10 base layer."""
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

    for encoding_id in encoding_ids:
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
                # 'dv81' (Dolby Vision Profile 8.1 / HDR10) or 'sdr' — keeps variant URIs unique
                # across the two ladders and lets the reader tell the dynamic range apart.
                label = 'sdr' if _is_sdr(video_codec) else 'dv81'

                # Two variants per video rendition (one per audio group). URIs include the DR label
                # and height to stay unique across ladders and bitrates.
                variants = []
                for audio_group in ('aac', 'atmos'):
                    variant = bitmovin_api.encoding.manifests.hls.streams.create(
                        manifest_id=hls_manifest.id,
                        stream_info=StreamInfo(
                            audio=audio_group,
                            closed_captions='NONE',
                            segment_path=segment_path,
                            uri=f'video_{label}_{video_codec.height}p_{video_codec.bitrate}_{audio_group}.m3u8',
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
                        filename=f'video_{label}_{video_codec.height}p_{video_codec.bitrate}_iframe.m3u8'))

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


def _is_sdr(video_codec):
    """True when an H265 codec config targets SDR (vs. the Dolby Vision Profile 8.1 ladder).
    Compares on the enum's string value so it works whether the SDK returns an enum or a string."""
    drf = video_codec.dynamic_range_format
    drf_value = drf.value if hasattr(drf, 'value') else drf
    return drf_value == H265DynamicRangeFormat.SDR.value


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
