import time
import datetime

from bitmovin_api_sdk import BitmovinApi
from bitmovin_api_sdk import S3Input, S3Output
from bitmovin_api_sdk import Encoding, CloudRegion
from bitmovin_api_sdk import EncodingOutput, AclEntry, AclPermission
from bitmovin_api_sdk import Stream, StreamInput, MuxingStream
from bitmovin_api_sdk import DolbyAtmosAudioConfiguration, DolbyAtmosLoudnessControl, DolbyAtmosMeteringMode
from bitmovin_api_sdk import DolbyAtmosDialogueIntelligence, DolbyAtmosIngestInputStream, DolbyAtmosInputFormat
from bitmovin_api_sdk import Mp4Muxing
from bitmovin_api_sdk import MessageType, StartEncodingRequest
from bitmovin_api_sdk import Status

API_KEY = '<INSERT YOUR API KEY>'
ORG_ID = '<INSERT YOUR ORG ID>'

S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

S3_OUTPUT_ACCESSKEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_OUTPUT_SECRETKEY = '<INSERT_YOUR_SECRET_KEY>'
S3_OUTPUT_BUCKETNAME = '<INSERT_YOUR_BUCKET_NAME>'

DOLBY_ATMOS_ADM_PATH = 'sollevante_lp_v01_DAMF_Nearfield_48k_24b_24.wav'  # from http://download.opencontent.netflix.com.s3.amazonaws.com/SolLevante/protools/ATMOS%20ADM%20%26%20DAMF%20Files.zip

date_component = str(datetime.datetime.now()).replace(' ', '__').replace(':', '-').split('.')[0]
ENCODING_NAME = 'Dolby Atmos Encoding - Progressive Mp4'
OUTPUT_BASE_PATH = 'output/{}/{}/'.format(ENCODING_NAME.replace(' - ', '__').replace(' ', '_'), date_component)

bitmovin_api = BitmovinApi(api_key=API_KEY, tenant_org_id=ORG_ID)


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

    # Create the ACL for output files
    acl_entry = AclEntry(permission=AclPermission.PUBLIC_READ)

    # Create an Encoding. This is the base entity used to configure the encoding.
    encoding = Encoding(name=ENCODING_NAME,
                        cloud_region=CloudRegion.AWS_AP_NORTHEAST_1,
                        encoder_version='STABLE')
    encoding = bitmovin_api.encoding.encodings.create(encoding=encoding)

    # Also the DolbyAtmos configuration has to be created
    atmos_config = DolbyAtmosAudioConfiguration(name='Atmos Codec Configuration',
                                                bitrate=448000,
                                                rate=48000,
                                                loudness_control=DolbyAtmosLoudnessControl(
                                                    metering_mode=DolbyAtmosMeteringMode.ITU_R_BS_1770_4,
                                                    dialogue_intelligence=DolbyAtmosDialogueIntelligence.ENABLED,
                                                    speech_threshold=15))
    atmos_config = bitmovin_api.encoding.configurations.audio.dolby_atmos.create(
        dolby_atmos_audio_configuration=atmos_config)

    # Create the input stream resources
    atmos_ingest_input_stream = DolbyAtmosIngestInputStream(
        input_id=s3_input.id,
        input_format=DolbyAtmosInputFormat.ADM,
        input_path=DOLBY_ATMOS_ADM_PATH
    )
    atmos_ingest_input_stream = bitmovin_api.encoding.encodings.input_streams.dolby_atmos.create(
        encoding_id=encoding.id, dolby_atmos_ingest_input_stream=atmos_ingest_input_stream)
    audio_input_stream = StreamInput(input_stream_id=atmos_ingest_input_stream.id)

    # create the stream for the audio
    audio_stream = Stream(codec_config_id=atmos_config.id,
                          input_streams=[audio_input_stream],
                          name='Audio Stream')
    audio_stream = bitmovin_api.encoding.encodings.streams.create(stream=audio_stream,
                                                                  encoding_id=encoding.id)

    # Create the MP4 muxing by combining both video and audio
    audio_muxing_stream = MuxingStream(stream_id=audio_stream.id)
    mp4_muxing_output = EncodingOutput(output_id=s3_output.id,
                                       output_path=OUTPUT_BASE_PATH,
                                       acl=[acl_entry])
    mp4_muxing = Mp4Muxing(name='Sample MP4 Muxing with Dolby Vision',
                           filename='output.mp4',
                           streams=[audio_muxing_stream],
                           outputs=[mp4_muxing_output])
    mp4_muxing = bitmovin_api.encoding.encodings.muxings.mp4.create(encoding_id=encoding.id,
                                                                    mp4_muxing=mp4_muxing)

    start_encoding_request = StartEncodingRequest()

    # Start the encoding
    execute_encoding(encoding=encoding, start_encoding_request=start_encoding_request)


def execute_encoding(encoding, start_encoding_request):
    bitmovin_api.encoding.encodings.start(encoding_id=encoding.id, start_encoding_request=start_encoding_request)

    task = wait_for_enoding_to_finish(encoding_id=encoding.id)
    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = wait_for_enoding_to_finish(encoding_id=encoding.id)

    if task.status is Status.ERROR:
        log_task_errors(task=task)
        raise Exception("Encoding failed")

    print("Encoding finished successfully")


def wait_for_enoding_to_finish(encoding_id):
    time.sleep(5)
    task = bitmovin_api.encoding.encodings.status(encoding_id=encoding_id)
    print("Encoding status is {} (progress: {} %)".format(task.status, task.progress))
    return task


def log_task_errors(task):
    if task is None:
        return

    filtered = filter(lambda msg: msg.type is MessageType.ERROR, task.messages)

    for message in filtered:
        print(message.text)


if __name__ == '__main__':
    main()
