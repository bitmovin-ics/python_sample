from bitmovin_api_sdk import BitmovinApi
from bitmovin_api_sdk import BitmovinApiLogger
from bitmovin_api_sdk import S3Input, S3Output
from bitmovin_api_sdk import Encoding, CloudRegion
from bitmovin_api_sdk import EncodingOutput, AclEntry, AclPermission
from bitmovin_api_sdk import Stream, StreamInput, MuxingStream, StreamMode, StreamSelectionMode
from bitmovin_api_sdk import ColorConfig, ColorSpace, ColorPrimaries, ColorTransfer
from bitmovin_api_sdk import H265VideoConfiguration, ProfileH265, PixelFormat
from bitmovin_api_sdk import MaxCtuSize, MotionSearch, TuInterDepth, TuIntraDepth, AdaptiveQuantMode
from bitmovin_api_sdk import AacAudioConfiguration, AacChannelLayout
from bitmovin_api_sdk import Fmp4Muxing
from bitmovin_api_sdk import PerTitle, H265PerTitleConfiguration, AutoRepresentation
from bitmovin_api_sdk import MessageType, Status, StartEncodingRequest
from bitmovin_api_sdk import DashManifest, Period
from bitmovin_api_sdk import VideoAdaptationSet, AudioAdaptationSet
from bitmovin_api_sdk import DashFmp4Representation
from bitmovin_api_sdk import DashRepresentationType, DashRepresentationTypeMode
from bitmovin_api_sdk import HlsManifest, HlsVersion
from bitmovin_api_sdk import AudioMediaInfo
from bitmovin_api_sdk import StreamInfo
from bitmovin_api_sdk import Trimming

import datetime
import time

API_KEY = '<INSERT YOUR API KEY>'
ORG_ID = '<INSERT YOUR ORG ID>'

S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

INPUT_PATH = "hdr10/Sony Bravia OLED 4K Demo.mp4" # from https://4kmedia.org/

S3_OUTPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_OUTPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_OUTPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

date_component = str(datetime.datetime.now()).replace(' ', '_').replace(':', '-').split('.')[0].replace('_', '__')
OUTPUT_BASE_PATH = 'encoding_test/hdr10_{}/'.format(date_component)

api = BitmovinApi(api_key=API_KEY, tenant_org_id=ORG_ID, logger=BitmovinApiLogger())

encoding_profiles_h265_pertitle = [
    dict(height=None, profile=ProfileH265.MAIN10, level=None, mode=StreamMode.PER_TITLE_TEMPLATE, aqs=1.2),
]

def main():
    # Create an S3 input. This resource is used as a base to acquire input files.
    s3_input = S3Input(name='Test S3 Input',
                       access_key=S3_INPUT_ACCESS_KEY,
                       secret_key=S3_INPUT_SECRET_KEY,
                       bucket_name=S3_INPUT_BUCKET_NAME)
    s3_input = api.encoding.inputs.s3.create(s3_input=s3_input)

    # Create an S3 Output. This will be used as the target bucket for the output files.
    s3_output = S3Output(name='Test S3 Output',
                         access_key=S3_OUTPUT_ACCESS_KEY,
                         secret_key=S3_OUTPUT_SECRET_KEY,
                         bucket_name=S3_OUTPUT_BUCKET_NAME)
    s3_output = api.encoding.outputs.s3.create(s3_output=s3_output)

    # Create the ACL for output files
    acl_entry = AclEntry(permission=AclPermission.PUBLIC_READ)

    # Create an Encoding. This is the base entity used to configure the encoding.
    encoding = Encoding(name='Sample HDR10 Encoding',
                        cloud_region=CloudRegion.AWS_AP_NORTHEAST_1,
                        encoder_version='STABLE')
    encoding = api.encoding.encodings.create(encoding=encoding)

    encoding_configs_per_title = []

    # Iterate over all encoding profiles and create the H265 configuration.
    for idx, _ in enumerate(encoding_profiles_h265_pertitle):
        profile_h265 = encoding_profiles_h265_pertitle[idx]
        encoding_config = dict(profile_h265=profile_h265)

        color_config = ColorConfig(color_space=ColorSpace.BT2020_NCL,
                                   color_primaries=ColorPrimaries.BT2020,
                                   color_transfer=ColorTransfer.SMPTE2084)

        h265_codec = H265VideoConfiguration(
            name='Sample video codec configuration',
            profile=profile_h265.get("profile"),
            height=profile_h265.get("height"),
            level=profile_h265.get("level"),
            pixel_format=PixelFormat.YUV420P10LE,
            bitrate=None,
            max_keyframe_interval=2,
            min_keyframe_interval=2,
            rate=None,
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
            adaptive_quantization_strength=profile_h265.get('aqs'),
            psy_rate_distortion_optimization=0,
            psy_rate_distortion_optimized_quantization=0,
            qp_min=15,
            sao=True,
            color_config=color_config,
            hdr=True,
            master_display='G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1)',
            max_content_light_level=800,
            max_picture_average_light_level=400
        )

        encoding_config['h265_codec'] = api.encoding.configurations.video.h265.create(h265_codec)
        encoding_configs_per_title.append(encoding_config)

    # Also the AAC configuration has to be created, which will be later on used to create the streams.
    audio_codec_configuration = AacAudioConfiguration(name='AAC Codec Configuration',
                                                      bitrate=128000,
                                                      rate=48000,
                                                      channel_layout=AacChannelLayout.CL_5_1_BACK)
    audio_codec_configuration = api.encoding.configurations.audio.aac.create(audio_codec_configuration)

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
        encoding_profile = encoding_config.get("profile_h265")
        video_stream = Stream(codec_config_id=encoding_config.get("h265_codec").id,
                              input_streams=[video_input_stream],
                              name='Stream H265 {}p'.format(encoding_profile.get('height')),
                              mode=encoding_profile.get('mode'))

        encoding_config['h265_stream'] = api.encoding.encodings.streams.create(stream=video_stream,
                                                                      encoding_id=encoding.id)

    # create the stream for the audio
    audio_stream = Stream(codec_config_id=audio_codec_configuration.id,
                          input_streams=[audio_input_stream],
                          name='Audio Stream')
    audio_stream = api.encoding.encodings.streams.create(stream=audio_stream,
                                                         encoding_id=encoding.id)

    # === Muxings ===
    for encoding_config in encoding_configs_per_title:
        encoding_profile = encoding_config.get("profile_h265")
        video_muxing_stream = MuxingStream(stream_id=encoding_config['h265_stream'].id)
        video_muxing_output = EncodingOutput(output_id=s3_output.id,
                                             output_path=OUTPUT_BASE_PATH + "video/{height}p_{bitrate}/",
                                             acl=[acl_entry])
        video_muxing = Fmp4Muxing(name="Video FMP4 Muxing {}p".format(encoding_profile.get('height')),
                                  streams=[video_muxing_stream],
                                  outputs=[video_muxing_output],
                                  init_segment_name='init.mp4',
                                  segment_naming='seg_%number%.m4s',
                                  segment_length=6)
        encoding_config['fmp4_muxing'] = api.encoding.encodings.muxings.fmp4.create(encoding_id=encoding.id,
                                                                           fmp4_muxing=video_muxing)

    audio_muxing_stream = MuxingStream(stream_id=audio_stream.id)
    audio_muxing_output = EncodingOutput(output_id=s3_output.id,
                                         output_path=OUTPUT_BASE_PATH + 'audio/',
                                         acl=[acl_entry])
    audio_fmp4_muxing = Fmp4Muxing(name='Audio FMP4 Muxing',
                                   streams=[audio_muxing_stream],
                                   outputs=[audio_muxing_output],
                                   init_segment_name='init.mp4',
                                   segment_naming='seg_%number%.m4s',
                                   segment_length=6)
    audio_fmp4_muxing = api.encoding.encodings.muxings.fmp4.create(encoding_id=encoding.id,
                                                          fmp4_muxing=audio_fmp4_muxing)

    # Keep the audio info together
    audio_representation_info = dict(
        fmp4_muxing=audio_fmp4_muxing,
        stream=audio_stream,
    )

    auto_representations = AutoRepresentation()
    h265_per_title_configuration = H265PerTitleConfiguration(auto_representations=auto_representations)
    per_title = PerTitle(h265_configuration=h265_per_title_configuration)

    start_encoding_request = StartEncodingRequest(per_title=per_title)

    # Start the encoding
    execute_encoding(encoding=encoding, start_encoding_request=start_encoding_request)

    # === DASH MANIFEST ===
    # Specify the output for manifest which will be in the OUTPUT_BASE_PATH.
    manifest_output = EncodingOutput(output_id=s3_output.id,
                                     output_path=OUTPUT_BASE_PATH,
                                     acl=[acl_entry])

    # Create a DASH manifest and add one period with an adapation set for audio and video
    dash_manifest = DashManifest(manifest_name='stream.mpd',
                                 outputs=[manifest_output],
                                 name='DASH Manifest')
    dash_manifest = api.encoding.manifests.dash.create(dash_manifest=dash_manifest)
    period = Period()
    period = api.encoding.manifests.dash.periods.create(period=period, manifest_id=dash_manifest.id)

    video_adaptation_set = VideoAdaptationSet()
    video_adaptation_set = api.encoding.manifests.dash.periods.adaptationsets.video.create(video_adaptation_set=video_adaptation_set,
                                                                                           manifest_id=dash_manifest.id,
                                                                                           period_id=period.id)

    audio_adaptation_set = AudioAdaptationSet(lang='en')
    audio_adaptation_set = api.encoding.manifests.dash.periods.adaptationsets.audio.create(audio_adaptation_set=audio_adaptation_set,
                                                                                           manifest_id=dash_manifest.id,
                                                                                           period_id=period.id)

    # Add the audio representation
    segment_path = audio_representation_info.get('fmp4_muxing').outputs[0].output_path
    segment_path = remove_output_base_path(segment_path)

    fmp4_representation_audio = DashFmp4Representation(encoding_id=encoding.id,
                                                       muxing_id=audio_representation_info.get('fmp4_muxing').id,
                                                       type_=DashRepresentationType.TEMPLATE,
                                                       mode=DashRepresentationTypeMode.TEMPLATE_REPRESENTATION,
                                                       segment_path=segment_path)
    api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(manifest_id=dash_manifest.id,
                                                                                   period_id=period.id,
                                                                                   adaptationset_id=audio_adaptation_set.id,
                                                                                   dash_fmp4_representation=fmp4_representation_audio)

    # Add all video representations to the video adaption set
    muxings = api.encoding.encodings.muxings.fmp4.list(encoding_id=encoding.id)
    for muxing in muxings.items:

        stream_id = muxing.streams[0].stream_id

        stream = api.encoding.encodings.streams.get(encoding_id=encoding.id,
                                                    stream_id=stream_id)
        stream_mode = stream.mode
        segment_path = muxing.outputs[0].output_path
        if 'audio' in segment_path:
            continue
        if stream_mode == StreamMode.PER_TITLE_TEMPLATE:
            continue

        segment_path = remove_output_base_path(segment_path)

        fmp4_representation = DashFmp4Representation(encoding_id=encoding.id,
                                                     muxing_id=muxing.id,
                                                     type_=DashRepresentationType.TEMPLATE,
                                                     mode=DashRepresentationTypeMode.TEMPLATE_REPRESENTATION,
                                                     segment_path=segment_path)

        fmp4_representation = api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
            manifest_id=dash_manifest.id,
            period_id=period.id,
            adaptationset_id=video_adaptation_set.id,
            dash_fmp4_representation=fmp4_representation)

    execute_dash_manifest(dash_manifest)

    # === HLS MANIFEST ===
    # Create a HLS manifest and add one period with an adapation set for audio and video
    hls_manifest = HlsManifest(manifest_name='stream.m3u8',
                               outputs=[manifest_output],
                               name='HLS Manifest',
                               hls_master_playlist_version=HlsVersion.HLS_V8,
                               hls_media_playlist_version=HlsVersion.HLS_V8)
    hls_manifest = api.encoding.manifests.hls.create(hls_manifest=hls_manifest)

    segment_path = audio_representation_info.get('fmp4_muxing').outputs[0].output_path
    segment_path = remove_output_base_path(segment_path)

    audio_media = AudioMediaInfo(name='HLS Audio Media',
                                 group_id='audio',
                                 language='en',
                                 segment_path=segment_path,
                                 encoding_id=encoding.id,
                                 stream_id=audio_representation_info.get('stream').id,
                                 muxing_id=audio_representation_info.get('fmp4_muxing').id,
                                 uri='audio.m3u8')
    audio_media = api.encoding.manifests.hls.media.audio.create(manifest_id=hls_manifest.id,
                                                                audio_media_info=audio_media)

    # Add all video representations to the video adaption set
    muxings = api.encoding.encodings.muxings.fmp4.list(encoding_id=encoding.id)
    for muxing in muxings.items:

        stream_id = muxing.streams[0].stream_id

        stream = api.encoding.encodings.streams.get(encoding_id=encoding.id,
                                                    stream_id=stream_id)
        stream_mode = stream.mode
        segment_path = muxing.outputs[0].output_path
        if 'audio' in segment_path:
            continue
        if stream_mode == StreamMode.PER_TITLE_TEMPLATE:
            continue

        segment_path = remove_output_base_path(segment_path)

        variant_stream = StreamInfo(audio=audio_media.group_id,
                                    closed_captions='NONE',
                                    segment_path=segment_path,
                                    uri='video_{}.m3u8'.format(muxing.avg_bitrate),
                                    encoding_id=encoding.id,
                                    stream_id=muxing.streams[0].stream_id,
                                    muxing_id=muxing.id)

        variant_stream = api.encoding.manifests.hls.streams.create(manifest_id=hls_manifest.id,
                                                                   stream_info=variant_stream)
    execute_hls_manifest(hls_manifest)

def execute_encoding(encoding, start_encoding_request):
    api.encoding.encodings.start(encoding_id=encoding.id, start_encoding_request=start_encoding_request)

    task = wait_for_enoding_to_finish(encoding_id=encoding.id)
    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = wait_for_enoding_to_finish(encoding_id=encoding.id)

    if task.status is Status.ERROR:
        log_task_errors(task=task)
        raise Exception("Encoding failed")

    print("Encoding finished successfully")

def wait_for_enoding_to_finish(encoding_id):
    time.sleep(5)
    task = api.encoding.encodings.status(encoding_id=encoding_id)
    print("Encoding status is {} (progress: {} %)".format(task.status, task.progress))
    return task

def execute_dash_manifest(dash_manifest):
    api.encoding.manifests.dash.start(manifest_id=dash_manifest.id)

    task = wait_for_dash_manifest_to_finish(manifest_id=dash_manifest.id)
    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = wait_for_dash_manifest_to_finish(manifest_id=dash_manifest.id)

    if task.status is Status.ERROR:
        log_task_errors(task=task)
        raise Exception("DASH Manifest generation failed")

    print("DASH Manifest generated successfully")

def execute_hls_manifest(hls_manifest):
    api.encoding.manifests.hls.start(manifest_id=hls_manifest.id)

    task = wait_for_hls_manifest_to_finish(manifest_id=hls_manifest.id)
    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = wait_for_hls_manifest_to_finish(manifest_id=hls_manifest.id)

    if task.status is Status.ERROR:
        log_task_errors(task=task)
        raise Exception("HLS Manifest generation failed")

    print("HLS Manifest generated successfully")

def wait_for_dash_manifest_to_finish(manifest_id):
    time.sleep(5)
    task = api.encoding.manifests.dash.status(manifest_id=manifest_id)
    print("DASH Manifest status is {} (progress: {} %)".format(task.status, task.progress))
    return task

def wait_for_hls_manifest_to_finish(manifest_id):
    time.sleep(5)
    task = api.encoding.manifests.hls.status(manifest_id=manifest_id)
    print("HLS Manifest status is {} (progress: {} %)".format(task.status, task.progress))
    return task

def log_task_errors(task):
    if task is None:
        return

    filtered = filter(lambda msg: msg.type is MessageType.ERROR, task.messages)

    for message in filtered:
        print(message.text)

def remove_output_base_path(text):
#    if not text.startswith('/'):
#        text = '/{}'.format(text)
    if text.startswith(OUTPUT_BASE_PATH):
        return text[len(OUTPUT_BASE_PATH):]
    return text

if __name__ == '__main__':
    main()
