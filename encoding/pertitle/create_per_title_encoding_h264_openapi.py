from bitmovin_api_sdk import BitmovinApi
from bitmovin_api_sdk import S3Input, S3Output
from bitmovin_api_sdk import Encoding, CloudRegion, EncodingMode
from bitmovin_api_sdk import EncodingOutput, AclEntry, AclPermission
from bitmovin_api_sdk import Stream, StreamInput, MuxingStream, StreamMode, StreamSelectionMode
from bitmovin_api_sdk import H264VideoConfiguration, ProfileH264
from bitmovin_api_sdk import H264MotionEstimationMethod, MvPredictionMode, AdaptiveQuantMode
from bitmovin_api_sdk import ColorConfig, H264Trellis, H264SubMe
from bitmovin_api_sdk import AacAudioConfiguration
from bitmovin_api_sdk import ScaleFilter, EnhancedWatermarkFilter, PositionUnit, StreamFilter
from bitmovin_api_sdk import Fmp4Muxing, TsMuxing
from bitmovin_api_sdk import MessageType, StartEncodingRequest
from bitmovin_api_sdk import DashManifest, Period
from bitmovin_api_sdk import VideoAdaptationSet, AudioAdaptationSet
from bitmovin_api_sdk import DashFmp4Representation
from bitmovin_api_sdk import DashRepresentationType
from bitmovin_api_sdk import HlsManifest
from bitmovin_api_sdk import AudioMediaInfo
from bitmovin_api_sdk import StreamInfo
from bitmovin_api_sdk import StreamPerTitleFixedResolutionAndBitrateSettings, BitrateSelectionMode
from bitmovin_api_sdk import PerTitle, PerTitleFixedResolutionAndBitrateConfiguration
from bitmovin_api_sdk import PerTitleFixedResolutionAndBitrateConfigurationMode
from bitmovin_api_sdk import StreamPerTitleSettings, H264PerTitleConfiguration
from bitmovin_api_sdk import Status

import pickle
import time
import datetime

API_KEY = '<INSERT YOUR API KEY>'
ORG_ID = '<INSERT YOUR ORG ID>'

S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

INPUT_PATH = '/path/to/your/input/file.mp4'

S3_OUTPUT_ACCESSKEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_OUTPUT_SECRETKEY = '<INSERT_YOUR_SECRET_KEY>'
S3_OUTPUT_BUCKETNAME = '<INSERT_YOUR_BUCKET_NAME>'

INPUT_HEIGHT=480
WATERMARK_WIDTH=51
WATERMARK_HEIGHT=18

date_component = str(datetime.datetime.now()).replace(' ', '_').replace(':', '-').split('.')[0].replace('_', '__')
OUTPUT_BASE_PATH = 'output/H264/{}/'.format(date_component)

bitmovin_api = BitmovinApi(api_key=API_KEY, tenant_org_id=ORG_ID)

encoding_profiles_h264_pertitle = [
    dict(height=180, profile=ProfileH264.BASELINE, level=None, mode=StreamMode.PER_TITLE_TEMPLATE, aqs=1.2),
    dict(height=360, profile=ProfileH264.MAIN, level=None, mode=StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, min=300000, max=500000, aqs=1.2),
    dict(height=360, profile=ProfileH264.MAIN, level=None, mode=StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, min=600000, max=900000, aqs=1.2),
    dict(height=540, profile=ProfileH264.MAIN, level=None, mode=StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, min=1000000, max=1400000, aqs=1.2),
    dict(height=720, profile=ProfileH264.HIGH, level=None, mode=StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE, min=1800000, max=2400000, aqs=1.0),
    dict(height=900, profile=ProfileH264.HIGH, level=None, mode=StreamMode.PER_TITLE_TEMPLATE, aqs=0.8),
    dict(height=1080, profile=ProfileH264.HIGH, level=None, mode=StreamMode.PER_TITLE_TEMPLATE, aqs=0.5),
]

def main():
    # Create an S3 input. This resource is then used as base to acquire input files.
    s3_input = S3Input(access_key=S3_INPUT_ACCESS_KEY,
                       secret_key=S3_INPUT_SECRET_KEY,
                       bucket_name=S3_INPUT_BUCKET_NAME,
                       name='Test S3 Input')
    s3_input = bitmovin_api.encoding.inputs.s3.create(s3_input=s3_input)

    # Create an S3 Output. This will be used as target bucket for the muxings, sprites and manifests
    s3_output = S3Output(access_key=S3_OUTPUT_ACCESSKEY,
                         secret_key=S3_OUTPUT_SECRETKEY,
                         bucket_name=S3_OUTPUT_BUCKETNAME,
                         name='Test S3 Output')
    s3_output = bitmovin_api.encoding.outputs.s3.create(s3_output=s3_output)

    # Create the ACL for Output Files
    acl_entry = AclEntry(permission=AclPermission.PUBLIC_READ)

    # Create an Encoding. This is the base entity used to configure the encoding.
    encoding = Encoding(name='Sample H264 Encoding',
                        cloud_region=CloudRegion.AWS_AP_NORTHEAST_1,
                        encoder_version='STABLE')
    encoding = bitmovin_api.encoding.encodings.create(encoding=encoding)

    encoding_configs_per_title = []

    # Iterate over all encoding profiles and create the H264 configuration.
    for idx, _ in enumerate(encoding_profiles_h264_pertitle):
        profile_h264 = encoding_profiles_h264_pertitle[idx]
        encoding_config = dict(profile_h264=profile_h264)

        color_config = ColorConfig(copy_color_primaries_flag=True,
                                   copy_color_transfer_flag=True,
                                   copy_color_space_flag=True)

        h264_codec = H264VideoConfiguration(
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
            color_config=color_config
        )
        pickle.dumps(h264_codec)
        encoding_config['h264_codec'] = bitmovin_api.encoding.configurations.video.h264.create(h264_video_configuration=h264_codec)
        encoding_configs_per_title.append(encoding_config)

    # Also the AAC configuration has to be created, which will be later on used to create the streams.
    aac_codec = AacAudioConfiguration(name='AAC Codec Configuration',
                                                      bitrate=128000,
                                                      rate=48000)
    aac_codec = bitmovin_api.encoding.configurations.audio.aac.create(aac_audio_configuration=aac_codec)

    # create the input stream resources
    video_input_stream = StreamInput(input_id=s3_input.id,
                                     input_path=INPUT_PATH,
                                     selection_mode=StreamSelectionMode.AUTO)
    audio_input_stream = StreamInput(input_id=s3_input.id,
                                     input_path=INPUT_PATH,
                                     selection_mode=StreamSelectionMode.AUTO)

    # With the configurations and the input file, streams are now created that will be muxed later on.
    # As we use per-title, the streams are used as templates
    for encoding_config in encoding_configs_per_title:
        encoding_profile = encoding_config.get("profile_h264")

        scale_filter = ScaleFilter(height=encoding_profile.get('height'), sample_aspect_ratio_numerator=1,
                                   sample_aspect_ratio_denominator=1)
        scale_filter = bitmovin_api.encoding.filters.scale.create(scale_filter=scale_filter)

        scaling = encoding_profile.get('height') / INPUT_HEIGHT

        wm_width = round(WATERMARK_WIDTH * scaling)
        wm_height = round(WATERMARK_HEIGHT * scaling)

        if encoding_profile.get('mode') == StreamMode.PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE:
            stream_fixed_res_bit_settings = StreamPerTitleFixedResolutionAndBitrateSettings(min_bitrate=encoding_profile.get('min'),
                                                                                            max_bitrate=encoding_profile.get('max'),
                                                                                            bitrate_selection_mode=BitrateSelectionMode.COMPLEXITY_RANGE,
                                                                                            low_complexity_boundary_for_max_bitrate=2160000,
                                                                                            high_complexity_boundary_for_max_bitrate=4000000)
            stream_per_title_settings = StreamPerTitleSettings(fixed_resolution_and_bitrate_settings=stream_fixed_res_bit_settings)

            video_stream = Stream(codec_config_id=encoding_config.get("h264_codec").id,
                                  input_streams=[video_input_stream],
                                  name='Stream H264 {}p'.format(encoding_profile.get('height')),
                                  mode=encoding_profile.get('mode'),
                                  per_title_settings=stream_per_title_settings)
        else:
            video_stream = Stream(codec_config_id=encoding_config.get("h264_codec").id,
                                  input_streams=[video_input_stream],
                                  name='Stream H264 {}p'.format(encoding_profile.get('height')),
                                  mode=encoding_profile.get('mode'))

        encoding_config['h264_stream'] = bitmovin_api.encoding.encodings.streams.create(encoding_id=encoding.id, stream=video_stream)

        bitmovin_api.encoding.encodings.streams.filters.create(encoding_id=encoding.id, stream_id=encoding_config['h264_stream'].id)

    # create the stream for the audio
    audio_stream = Stream(codec_config_id=aac_codec.id,
                          input_streams=[audio_input_stream],
                          name='Audio Stream')
    audio_stream = bitmovin_api.encoding.encodings.streams.create(encoding_id=encoding.id, stream=audio_stream)

    # === Muxings ===
    for encoding_config in encoding_configs_per_title:
        encoding_profile = encoding_config.get("profile_h264")
        video_muxing_stream = MuxingStream(stream_id=encoding_config['h264_stream'].id)
        video_muxing_output = EncodingOutput(output_id=s3_output.id,
                                             output_path=OUTPUT_BASE_PATH + "video/dash/{height}p_{bitrate}/",
                                             acl=[acl_entry])
        video_muxing = Fmp4Muxing(segment_length=6,
                                  segment_naming='seg_%number%.m4s',
                                  init_segment_name='init.mp4',
                                  streams=[video_muxing_stream],
                                  outputs=[video_muxing_output],
                                  name="Video FMP4 Muxing {}p".format(encoding_profile.get('height')))

        encoding_config['fmp4_muxing'] = bitmovin_api.encoding.encodings.muxings.fmp4.create(encoding_id=encoding.id, fmp4_muxing=video_muxing)

        video_muxing_output = EncodingOutput(output_id=s3_output.id,
                                             output_path=OUTPUT_BASE_PATH + "video/hls/{height}p_{bitrate}/",
                                             acl=[acl_entry])
        video_muxing = TsMuxing(segment_length=6,
                                segment_naming='seg_%number%.ts',
                                streams=[video_muxing_stream],
                                outputs=[video_muxing_output],
                                name='Video TS Muxing {}p'.format(encoding_profile.get('height')))
        encoding_config['ts_muxing'] = bitmovin_api.encoding.encodings.muxings.ts.create(encoding_id=encoding.id, ts_muxing=video_muxing)

    audio_muxing_stream = MuxingStream(stream_id=audio_stream.id)
    audio_muxing_output = EncodingOutput(output_id=s3_output.id,
                                         output_path=OUTPUT_BASE_PATH + 'audio/dash/',
                                         acl=[acl_entry])
    audio_fmp4_muxing = Fmp4Muxing(segment_length=6,
                                   segment_naming='seg_%number%.m4s',
                                   init_segment_name='init.mp4',
                                   streams=[audio_muxing_stream],
                                   outputs=[audio_muxing_output],
                                   name='Audio FMP4 Muxing')
    audio_fmp4_muxing = bitmovin_api.encoding.encodings.muxings.fmp4.create(encoding_id=encoding.id, fmp4_muxing=audio_fmp4_muxing)

    audio_muxing_stream = MuxingStream(stream_id=audio_stream.id)
    audio_muxing_output = EncodingOutput(output_id=s3_output.id,
                                         output_path=OUTPUT_BASE_PATH + 'audio/hls/',
                                         acl=[acl_entry])
    audio_ts_muxing = TsMuxing(segment_length=6,
                               segment_naming='seg_%number%.ts',
                               streams=[audio_muxing_stream],
                               outputs=[audio_muxing_output],
                               name='Audio TS Muxing')
    audio_ts_muxing = bitmovin_api.encoding.encodings.muxings.ts.create(encoding_id=encoding.id, ts_muxing=audio_ts_muxing)

    # Keep the audio info together
    audio_representation_info = dict(
        fmp4_muxing=audio_fmp4_muxing,
        ts_muxing=audio_ts_muxing,
        stream=audio_stream,
    )

    # Finally create the per-title configuration to pass to the encoding
    fixed_resolution_and_bitrate_configuration = PerTitleFixedResolutionAndBitrateConfiguration(forced_rendition_above_highest_fixed_representation=1,
                                                                                                forced_rendition_above_highest_fixed_representation_factor=1.2,
                                                                                                forced_rendition_above_highest_fixed_representation_calculation_mode=PerTitleFixedResolutionAndBitrateConfigurationMode.LAST_CALCULATED_BITRATE)

    h264_per_title_configuration = H264PerTitleConfiguration(min_bitrate=128000, max_bitrate=4000000, codec_min_bitrate_factor=0.8,
                                                             codec_max_bitrate_factor=1.2, codec_bufsize_factor=2.0,
                                                             target_quality_crf=17, complexity_factor=1.0,
                                                             fixed_resolution_and_bitrate_configuration=fixed_resolution_and_bitrate_configuration,
                                                             max_bitrate_step_size=4.0)

    per_title = PerTitle(h264_configuration=h264_per_title_configuration)

    # And start the encoding
    start_encoding_request = StartEncodingRequest(per_title=per_title,encoding_mode=EncodingMode.THREE_PASS)
    _execute_encoding(encoding=encoding, start_encoding_request=start_encoding_request)

    # Specify the output for manifest which will be in the OUTPUT_BASE_PATH.
    manifest_output = EncodingOutput(output_id=s3_output.id,
                                     output_path=OUTPUT_BASE_PATH,
                                     acl=[acl_entry])

    # === DASH MANIFEST ===
    # Create a DASH manifest and add one period with an adapation set for audio and video
    dash_manifest = DashManifest(manifest_name='stream.mpd',
                                 outputs=[manifest_output],
                                 name='DASH Manifest')
    dash_manifest = bitmovin_api.encoding.manifests.dash.create(dash_manifest=dash_manifest)
    period = Period()
    period = bitmovin_api.encoding.manifests.dash.periods.create(manifest_id=dash_manifest.id, period=period)\

    video_adaptation_set = VideoAdaptationSet()
    video_adaptation_set = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.video.create(manifest_id=dash_manifest.id, period_id=period.id, video_adaptation_set=video_adaptation_set)

    audio_adaptation_set = AudioAdaptationSet(lang='en')
    audio_adaptation_set = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.audio.create(manifest_id=dash_manifest.id, period_id=period.id, audio_adaptation_set=audio_adaptation_set)

    # Add the audio representation
    segment_path = audio_representation_info.get('fmp4_muxing').outputs[0].output_path
    segment_path = remove_output_base_path(segment_path)

    fmp4_representation_audio = DashFmp4Representation(type_=DashRepresentationType.TEMPLATE,
                                                       encoding_id=encoding.id,
                                                       muxing_id=audio_representation_info.get('fmp4_muxing').id,
                                                       segment_path=segment_path)
    bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(manifest_id=dash_manifest.id,
                                                                                            period_id=period.id,
                                                                                            adaptationset_id=audio_adaptation_set.id    ,
                                                                                            dash_fmp4_representation=fmp4_representation_audio)

    # Add all video representations to the video adaption set
    muxings = bitmovin_api.encoding.encodings.muxings.fmp4.list(encoding_id=encoding.id)
    for muxing in muxings.items:

        stream_id = muxing.streams[0].stream_id

        stream = bitmovin_api.encoding.encodings.streams.get(encoding_id=encoding.id, stream_id=stream_id)

        stream_mode = stream.mode
        segment_path = muxing.outputs[0].output_path
        if 'audio' in segment_path:
            continue
        if 'PER_TITLE_TEMPLATE' in stream_mode.value:
            continue

        segment_path = remove_output_base_path(segment_path)

        fmp4_representation = DashFmp4Representation(
            type_=DashRepresentationType.TEMPLATE,
            encoding_id=encoding.id,
            muxing_id=muxing.id,
            segment_path=segment_path,
        )
        fmp4_representation = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(manifest_id=dash_manifest.id,
                                                                                                                      period_id=period.id,
                                                                                                                      adaptationset_id=video_adaptation_set.id,
                                                                                                                      dash_fmp4_representation=fmp4_representation)
    _execute_dash_manifest_generation(dash_manifest=dash_manifest)

    # === HLS MANIFEST ===
    # Create a HLS manifest and add one period with an adapation set for audio and video
    hls_manifest = HlsManifest(manifest_name='stream.m3u8',
                               outputs=[manifest_output],
                               name='HLS Manifest')
    hls_manifest = bitmovin_api.encoding.manifests.hls.create(hls_manifest=hls_manifest)

    segment_path = audio_representation_info.get('ts_muxing').outputs[0].output_path
    segment_path = remove_output_base_path(segment_path)

    audio_media = AudioMediaInfo(name='HLS Audio Media',
                                 group_id='audio',
                                 segment_path=segment_path,
                                 encoding_id=encoding.id,
                                 stream_id=audio_representation_info.get('stream').id,
                                 muxing_id=audio_representation_info.get('ts_muxing').id,
                                 language='en',
                                 uri='audio.m3u8')
    audio_media = bitmovin_api.encoding.manifests.hls.media.audio.create(manifest_id=hls_manifest.id,
                                                                         audio_media_info=audio_media)

    # Add all video representations to the video adaption set
    muxings = bitmovin_api.encoding.encodings.muxings.ts.list(encoding_id=encoding.id)
    for muxing in muxings.items:

        stream_id = muxing.streams[0].stream_id

        stream = bitmovin_api.encoding.encodings.streams.get(encoding_id=encoding.id, stream_id=stream_id)

        stream_mode = stream.mode
        segment_path = muxing.outputs[0].output_path
        if 'audio' in segment_path:
            continue
        if 'PER_TITLE_TEMPLATE' in stream_mode.value:
            continue

        segment_path = remove_output_base_path(segment_path)

        variant_stream = StreamInfo(audio=audio_media.group_id,
                                    closed_captions='NONE',
                                    segment_path=segment_path,
                                    uri='video_{}.m3u8'.format(muxing.avg_bitrate),
                                    encoding_id=encoding.id,
                                    stream_id=muxing.streams[0].stream_id,
                                    muxing_id=muxing.id)
        variant_stream = bitmovin_api.encoding.manifests.hls.streams.create(manifest_id=hls_manifest.id, stream_info=variant_stream)

    _execute_hls_manifest_generation(hls_manifest=hls_manifest)

def remove_output_base_path(text):
    if text.startswith(OUTPUT_BASE_PATH):
        return text[len(OUTPUT_BASE_PATH):]
    return text

def _execute_encoding(encoding, start_encoding_request):
    bitmovin_api.encoding.encodings.start(encoding_id=encoding.id, start_encoding_request=start_encoding_request)

    task = _wait_for_enoding_to_finish(encoding_id=encoding.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_enoding_to_finish(encoding_id=encoding.id)

    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("Encoding failed")

    print("Encoding finished successfully")

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

    print("DASH Manifest Creation finished successfully")

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

def _log_task_errors(task):
    if task is None:
        return

    filtered = filter(lambda msg: msg.type is MessageType.ERROR, task.messages)

    for message in filtered:
        print(message.text)

if __name__ == '__main__':
    main()
