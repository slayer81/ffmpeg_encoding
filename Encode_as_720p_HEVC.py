#!/usr/local/bin/python3.11
import os
import sys
import pathlib
import subprocess
import datetime as dt
import humanize as hm

####################################################################################
# Global variables
####################################################################################
START_TIME = dt.datetime.now()
MARKER_CHAR = '#'

# Define Trash Directory
TRASH_DIR = '/Users/scott/.Trash/'

# Define Archive_Fail_Over_Dir
ARCHIVE_FAIL_OVER_DIR = '/Users/scott/_Encoder_Archive'

# Notification Parameters
MSG_TITLE = 'Encode as 720p HEVC'

# Logging Parameters
TODAY_DATESTAMP = dt.date.today().strftime("%Y-%m-%d")
LOG_SPACER = '   '
SPACER = ' '
LOG_DIR = '/Users/scott/Logs/ffmpeg/Encode_as_720p_HEVC'
LOG_NAME = f'{TODAY_DATESTAMP}.log'
LOGFILE_FULL_PATH = os.path.join(LOG_DIR, LOG_NAME)

# Create "LOG_DIR" if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)
####################################################################################
# End Globals


####################################################################################
# Function to calculate percentages
def percentage(part, whole):
    return round((100 * float(part) / float(whole)), 2)
####################################################################################


####################################################################################
# Function to calculate percent decrease
def percentage_decrease(new, old):
    return round((((float(old) - float(new)) / float(old)) * 100), 2)
####################################################################################


####################################################################################
def logger(status, data):    
    status_list = ['none', 'info', 'success', 'failure', 'warning']
    if status.lower() not in status_list:
        status_key = 'UNKNOWN'
    else:
        status_key = status.upper()

    # Write to logfile
    with open(LOGFILE_FULL_PATH, "a") as log_pipe:
        log_timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        if status_key == 'NONE':
            log_data = data
        else:
            log_data = '{:23} || {:^7} || {:<80}\n'.format(log_timestamp, status_key, data)
        log_pipe.write(f'{log_data}')
####################################################################################


####################################################################################
def file_event(action, command):
    try:
        subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger('success', f'{SPACER * 3} File {action}d successfully')
        return 0
    except Exception:
        logger('failure', f'{SPACER * 3} Failed to {action} file. Please perform manually')
        return 1
####################################################################################


####################################################################################
def create_notification_content(total_count, failed_list, e_time, pc_saved):
    message_content_list = [MSG_TITLE]
    msg_body = ''

    if len(failed_list) > 0:
        msg_subtitle = f'FAILED to encode {len(failed_list)} of {total_count} files'
        msg_body += f'Check the log file for a list of specific files\n{LOGFILE_FULL_PATH}'
    else:
        msg_subtitle = f'All {total_count} files were encoded successfully'

    msg_body += f'Disk space recovered: {pc_saved}\nTotal runtime: {e_time}'
    message_content_list.extend([msg_subtitle, msg_body])

    if len(message_content_list) == 3:
        message_content = '|'.join(message_content_list)
    else:
        message_content = f' Automator Task Completed With Errors | Check Log File For More Detail | {LOGFILE_FULL_PATH} '
    return message_content
####################################################################################


####################################################################################
def encode(target_file):
    p = pathlib.Path(target_file)
    ppp = pathlib.PurePosixPath(target_file)
    ts_now = dt.datetime.now()
    metadata_title = ppp.stem.replace('.', ' ')
    output_dir = p.resolve().parent
    output_file_stem = str(ppp.stem)
    output_file_ext = str(ppp.suffix)
    temp_file_name = f'{output_file_stem}.TEMP{output_file_ext}'
    temp_file_full_path = os.path.join(p.parent, temp_file_name)
    before_size_raw = os.path.getsize(target_file)
    before_size = hm.naturalsize(before_size_raw)

    # Use pathlib to extract the volume name parts, else use TRASH_DIR
    # Assemble the volume name with safety checks
    if len(p.parts) >= 3:
        volume = str(p.parts[0] + p.parts[1] + '/' + p.parts[2])
        encoder_archive = os.path.join(volume, '_Encoder_Archive')
    else:
        encoder_archive = ARCHIVE_FAIL_OVER_DIR

    # Create "encoder_archive" if it doesn't exist
    os.makedirs(encoder_archive, exist_ok=True)
    
    # archive_file_full_path = os.path.join(encoder_archive, p.name)

    logger('info', f'{SPACER * 3} File:  "{target_file}"')
    logger('info', f'{SPACER * 3} Source file path:\t {output_dir}')
    logger('info', f'{SPACER * 3} Source file name:\t {p.name}')
    logger('info', f'{SPACER * 3} Source file size:\t {before_size}')

    # Create filename for our working copy, before downgrading.
    temp_file = os.path.join(output_dir, temp_file_name)

    # ffmpeg Parameters
    ff_bin = '/usr/local/bin/ffmpeg -hide_banner -i'
    # ff_switches = f'-vf "scale=-1:720" -c:v libx265 -crf 25 -preset medium -c:a copy -map_metadata 0 -metadata title="{metadata_title}"'
    ff_switches = f'-vf "scale=-1:720" -c:v libx265 -crf 25 -preset medium -c:a copy -map_metadata -1 -metadata title="{metadata_title}"'

    convert_cmd = f'{ff_bin} "{target_file}" {ff_switches} "{temp_file}"'
    repl_src_file_cmd = f'mv -f "{temp_file}" "{target_file}"'
    del_tmp_file_cmd = f'mv "{temp_file}" "{TRASH_DIR}"'
    del_src_file_cmd = f'rm -f "{target_file}"'
    arc_src_file_cmd = f'mv "{target_file}" "{encoder_archive}"'

    # Convert File
    logger('info', f'{SPACER * 3} Begin encoding of target file....')
    try:
        subprocess.run(convert_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    except Exception as e:
        # Downgrade process failed. Log event
        logger('failure', f'{SPACER * 3}')
        logger('failure', f'{SPACER * 6} *** Encoding failed *** Response: "{str(e)}". Cleaning up.....')
        logger('failure', f'{SPACER * 3}')

        # Delete temp file
        logger('info', f'{SPACER * 3} Deleting temp file')
        file_event('delete', del_tmp_file_cmd)
        return 0, p.name, before_size_raw, before_size_raw

    # Downgraded successfully
    after_size_raw = os.path.getsize(temp_file_full_path)
    after_size = hm.naturalsize(after_size_raw)

    # logger('success', f'{SPACER * 3} Successfully encoded "{target_file}"!')
    logger('success', f'{SPACER * 3} Successfully encoded "{temp_file_name}"!')
    logger('info', f'{SPACER * 3} Encoded file size:\t {after_size}\t Reduction:\t ({percentage_decrease(after_size_raw, before_size_raw)}%)')

    # Move target_file to encoder_archive
    logger('info', f'{SPACER * 3} Moving source file to encoder archive')
    # file_event('rename', arc_src_file_cmd)
    file_event('move', arc_src_file_cmd)

    # Overwrite target_file with temp_file
    # Rename encoded file as original
    logger('info', f'{SPACER * 3} Renaming encoded file as source file name')
    file_event('rename', repl_src_file_cmd)
    logger('info', f'{SPACER * 3} File encoding process completed')

    execution_time = hm.precisedelta(dt.datetime.now() - ts_now)
    logger('info', '{:<62} {:>16}'.format('File processing time:', execution_time))
    return 1, p.name, before_size_raw, after_size_raw
####################################################################################


####################################################################################
def main():
    logger('none', f'\n\n{MARKER_CHAR * 140}\n')
    logger('info', f'Starting encoder script:\t {__file__}')
    logger('info', 'Checking for targets.... ')
    logger('none', f'{MARKER_CHAR * 140}\n')
    if len(sys.argv) > 1:
        if isinstance(sys.argv[1], int):
            targets_list = sys.argv[2:]
            logger('info', f"Found {(len(targets_list))} targets to encode. Let's begin!")
        else:
            targets_list = sys.argv[1:]
            logger('info', f"Found {(len(targets_list))} targets to encode. Let's begin!")
    else:
        logger('failure', f' *** Nothing found to encode ***. Exiting.....')
        logger('info', f'{MARKER_CHAR * 100}')

        execution_time = hm.precisedelta(dt.datetime.now() - START_TIME)
        message_content = f' Automator Task Completed | {MSG_TITLE} | Nothing found to encode\nTotal runtime: {execution_time} '
        logger('info', f'Display Notification data:\t"{message_content[20:]}"...')
        logger('info', '{:<62} {:>16}'.format(f'Execution completed. Total runtime:', execution_time))
        logger('none', f'{MARKER_CHAR * 140}\n')
        print(message_content)

        # Make sure to flush stdout to ensure immediate output
        sys.stdout.flush()
        exit(0)

    loop_counter = 1
    success_counter = 0
    failed_list = []
    before_size_raw = 0
    after_size_raw = 0
    for f in targets_list:
        logger('info', f'{MARKER_CHAR * 100}')
        logger('info', f'Target ({loop_counter} of {len(targets_list)})')
        # result, name, old_size, new_size = encode(f)
        result, name, old_size, new_size = encode(f)
        success_counter = success_counter + result
        if result == 0:
            failed_list.append(name)
        before_size_raw += old_size
        after_size_raw += new_size
        loop_counter += 1

    before_size = hm.naturalsize(before_size_raw)
    after_size = hm.naturalsize(after_size_raw)
    percent_size_reduced = percentage_decrease(after_size_raw, before_size_raw)
    logger('info', f'{MARKER_CHAR * 100}')


    logger('info', '{:>35} {:>16}'.format('Total file size (targets passed): ', before_size))
    logger('info', '{:>35} {:>16}'.format('Total file size (after encoding): ', after_size))
    logger('info', '{:>35} {:>16}'.format('Total reduction in disk space: ', percent_size_reduced))

    
    execution_time = hm.precisedelta(dt.datetime.now() - START_TIME)
    message_content = create_notification_content(len(targets_list), failed_list, execution_time, f'{str(percent_size_reduced)}%')
    # logger('success', f'Display Notification data:\t"{message_content[20:]}"...')
    logger('info', '{:<62} {:>16}'.format(f'Execution completed. Total runtime:', execution_time))
    logger('none', f'{MARKER_CHAR * 140}\n')

    # Print notification content to stdout
    print(message_content)

    # Make sure to flush stdout to ensure immediate output
    sys.stdout.flush()
####################################################################################


####################################################################################
if __name__ == "__main__":
    main()
