#!/usr/local/bin/python3.11
import os
import sys
import pathlib
import subprocess
import datetime as dt
import humanize as hm
import re
import shutil

####################################################################################
# Global variables
####################################################################################
FILE_STUB = os.path.basename(__file__).replace('.py', '')
START_TIME = dt.datetime.now()
MARKER_CHAR = '#'
SPACER = ' '

# Define Trash Directory
TRASH_DIR = '/Users/scott/.Trash/'

# Define Archive_Fail_Over_Dir
ARCHIVE_FAIL_OVER_DIR = '/Users/scott/_Encoder_Archive'

# Logging Parameters
TODAY_DATESTAMP = dt.date.today().strftime("%Y-%m-%d")
LOG_SPACER = '   '
LOG_DIR = f'/Users/scott/Logs/ffmpeg/{FILE_STUB}'
LOG_NAME = f'{TODAY_DATESTAMP}.log'
LOGFILE_FULL_PATH = os.path.join(LOG_DIR, LOG_NAME)

# Create "LOG_DIR" if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# ffmpeg Parameters
FF_BIN = '/usr/local/bin/ffmpeg'
FF_EXECUTION_FLAGS = ['-hide_banner',  '-i']
# VIDEO_PARAMS = ['-c:v', 'libx265', '-tag:v', 'hvc1', '-b:v', '1500k', '-pix_fmt', 'yuv420p']
VIDEO_PARAMS = ['-c:v', 'libx265', '-tag:v', 'hvc1', '-crf', '25', '-pix_fmt', 'yuv420p']
AUDIO_PARAMS = ['-c:a', 'aac', '-b:a', '192k']
FF_SWITCHES = [*VIDEO_PARAMS, *AUDIO_PARAMS, '-map_metadata', '-1', '-metadata']
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
# Function to enclose object year in parentheses
def enclose_year_in_parentheses(text):
	return re.sub(r'(\b\d{4}\b)$', r'(\1)', text)
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
def human_but_smaller(data: str):
	swap_dict = {
		' and': '',
		' hour': ' hr',
		' minute': ' min',
		' seconds': ' sec'
	}
	for key, value in swap_dict.items():
		data = data.replace(key, value)
	return data
####################################################################################


####################################################################################
def create_notification_content(total_count, failed_list, body_str):
	MSG_TITLE = f'({dt.datetime.now().strftime("%H:%M")})\t{FILE_STUB.replace("_", " ")}'
	message_content_list = [MSG_TITLE]
	msg_body = ''

	if len(failed_list) > 0:
		msg_subtitle = f'FAILED to encode {len(failed_list)} of {total_count} files'
		msg_body += f'Filenames in log: "{LOG_NAME}"\n'
	else:
		msg_subtitle = f'All {total_count} files were encoded successfully'

	msg_body += f'{body_str}'
	message_content_list.extend([msg_subtitle, body_str])

	if len(message_content_list) == 3:
		message_content = '|'.join(message_content_list)
	else:
		message_content = f' Automator Task Completed With Errors | Check Log File For More Detail | {LOG_NAME} '
	return message_content
####################################################################################


####################################################################################
def encode(target_file):
	p = pathlib.Path(target_file)
	ppp = pathlib.PurePosixPath(target_file)
	ts_now = dt.datetime.now()
	metadata_title = ppp.stem.replace('.', ' ').replace('-', ':')
	output_dir = p.resolve().parent
	output_file_stem = str(ppp.stem)
	output_file_ext = str(ppp.suffix)
	temp_file_name = f'{output_file_stem}.TEMP{output_file_ext}'
	before_size_raw = os.path.getsize(target_file)

	# Use pathlib to extract the volume name parts, else use ARCHIVE_FAIL_OVER_DIR
	# Assemble the volume name with safety checks
	if len(p.parts) >= 3:
		volume = str(p.parts[0] + p.parts[1] + '/' + p.parts[2])
		encoder_archive = os.path.join(volume, '_Encoder_Archive')
	else:
		encoder_archive = ARCHIVE_FAIL_OVER_DIR

	# Create "encoder_archive" if it doesn't exist
	os.makedirs(encoder_archive, exist_ok=True)

	logger('info', f'{SPACER * 3} Target file path:\t {output_dir}')
	logger('info', f'{SPACER * 3} Target file name:\t {p.name}')
	logger('info', f'{SPACER * 3} Target file title:\t {metadata_title}')
	logger('info', f'{SPACER * 3} Target file size:\t {hm.naturalsize(before_size_raw)}')

	# Create filename for our working copy, before downgrading.
	temp_file = os.path.join(output_dir, temp_file_name)

	# Assemble metadata title string
	metadata_title_string = ''.join(['title="', metadata_title, '"'])

	# ffmpeg command
	convert_cmd = [
		FF_BIN,
		*FF_EXECUTION_FLAGS,
		target_file,
		*FF_SWITCHES,  # Correct: Unpacks the list into separate arguments
		metadata_title_string,
		temp_file
	]

	# Convert File
	logger('info', f'{SPACER * 3} Begin encoding of target file....')
	try:
		subprocess.run(convert_cmd, shell=False, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		logger('success', f'{SPACER * 3} File encoded successfully')

		# Downgraded successfully
		after_size_raw = os.path.getsize(temp_file)
		after_size = hm.naturalsize(after_size_raw)

		# Move original file to encoder_archive
		logger('info', f'{SPACER * 3} Archiving source file')
		try:
			shutil.move(target_file, encoder_archive)
			logger('success', f'{SPACER * 3} File Archived successfully')
		except Exception as e:
			logger('failure', f'{SPACER * 3} Failed to archive file. Please perform manually')
			logger('failure', f'{SPACER * 3} Response:\t {str(e)}')

		# Rename encoded file as original file name
		logger('info', f'{SPACER * 3} Renaming encoded file')
		try:
			shutil.move(temp_file, target_file)
			logger('success', f'{SPACER * 3} File Renamed successfully')
		except Exception as e:
			logger('failure', f'{SPACER * 3} Failed to rename file. Please perform manually')
			logger('failure', f'{SPACER * 3} Response:\t {str(e)}')

		logger('info', f'{SPACER * 3}  Encoded file size:\t {after_size}')
		logger('info', f'{SPACER * 3} Capacity recovered:\t {percentage_decrease(after_size_raw, before_size_raw)}%')


		execution_time = hm.precisedelta(dt.datetime.now() - ts_now)
		logger('info', '{:<50} {:>16}'.format('File processing time:', execution_time))
		return 1, p.name, before_size_raw, after_size_raw

	except Exception as e:
		# Encoding process failed. Log event
		logger('failure', f'{SPACER * 3}')
		logger('failure', f'{SPACER * 6} *** Encoding failed *** Response: "{str(e)}"')
		logger('failure', f'{SPACER * 6} *** Cleaning up.....')
		logger('failure', f'{SPACER * 3}')

		# Delete temp file
		logger('info', f'{SPACER * 3} Deleting TEMP file')

		try:
			shutil.move(temp_file, TRASH_DIR)
			logger('success', f'{SPACER * 3} Successfully deleted TEMP file')
		except Exception as e:
			logger('failure', f'{SPACER * 3} Failed to delete TEMP file. Please perform manually')
			logger('failure', f'{SPACER * 3} Response:\t {str(e)}')
		return 0, p.name, before_size_raw, before_size_raw
####################################################################################


####################################################################################
def main():
	logger('none', f'\n\n{MARKER_CHAR * 140}\n')
	logger('info', f'Executing script:\t {__file__}')
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
		MSG_TITLE = 'BORK BORK'
		message_content = f' Automator Task Completed | {MSG_TITLE} | Nothing found to encode\nTotal runtime: {human_but_smaller(execution_time)} '
		logger('info', f'Display Notification data:\t"{message_content[20:]}"...')
		logger('info', '{:<62} {:>16}'.format(f'Execution completed. Total runtime:', human_but_smaller(execution_time)))
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
		result, name, old_size, new_size = encode(f)
		success_counter = success_counter + result
		if result == 0:
			failed_list.append(name)
		before_size_raw += old_size
		after_size_raw += new_size
		loop_counter += 1
	logger('info', f'{MARKER_CHAR * 100}')

	execution_time = hm.precisedelta(dt.datetime.now() - START_TIME)
	saved_size = hm.naturalsize(before_size_raw - after_size_raw)
	body_str = 'Disk space recovered:  {}   ({}%)\nAvg. encode time: {}\nTime: {}'.format(
		saved_size, percentage_decrease(after_size_raw, before_size_raw),
		human_but_smaller(hm.precisedelta((dt.datetime.now() - START_TIME) / len(targets_list))),
		human_but_smaller(execution_time)
	)

	# Print notification content to stdout
	message_content = create_notification_content(len(targets_list), failed_list, body_str)
	print(message_content)

	# Make sure to flush stdout to ensure immediate output
	sys.stdout.flush()

	# Write cumulative results to logfile
	logger('info', '{:>35} {:>16}'.format('  Total file size (targets passed): ', hm.naturalsize(before_size_raw)))
	logger('info', '{:>35} {:>16}'.format('  Total file size (after encoding): ', hm.naturalsize(after_size_raw)))
	logger('info', '{:>35} {:5} {:<16}'.format(
		'Average file re-encoding time: ', '',
		human_but_smaller(hm.precisedelta((dt.datetime.now() - START_TIME) / len(targets_list)))
#     	human_but_smaller(execution_time / len(targets_list)))
	))
	logger('info', '{:>35} {:>16}'.format('  Total disk space recovered: ', saved_size))
	if failed_list:
		logger('info', '{:>36} {:>16}'.format('         Encoding failed for: ', f'{len(failed_list)} objects'))
	execution_time = hm.precisedelta(dt.datetime.now() - START_TIME)

	logger('info', '{:<42} {:>16}'.format(f'Execution completed. Total runtime: ', human_but_smaller(execution_time)))
	logger('none', f'{MARKER_CHAR * 140}\n')
####################################################################################


####################################################################################
if __name__ == "__main__":
	main()
