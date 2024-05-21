import pandas as pd
from datetime import datetime, timedelta, timezone
import yaml
import glob
import argparse
from tzlocal import get_localzone

def get_file_path(file_type, extension):
    files = [file for file in glob.glob(f"*.{extension}") if file != 'output.csv']
    if len(files) == 1:
        return files[0]
    elif len(files) > 1:
        print(f"Multiple {file_type} files found: {', '.join(files)}")
        return input(f"Enter the path for the {file_type} file: ")
    else:
        return input(f"Enter the path for the {file_type} file: ")

parser = argparse.ArgumentParser(description="Process quiz entry and gradescope submission times.")
parser.add_argument('-c', '--csv', type=str, help="Path to the CSV file.", dest='csv')
parser.add_argument('-y', '--yml', type=str, help="Path to the YAML file.", dest='yml')
parser.add_argument('-t', '--time', type=str, help="Time limit in format HH:MM:SS", dest='time_limit', required=True)

args = parser.parse_args()

file_path1 = args.csv if args.csv else get_file_path('CSV', 'csv')
file_path2 = args.yml if args.yml else get_file_path('YAML', 'yml')

df1 = pd.read_csv(file_path1)
df1.columns = df1.columns.str.strip()
df1['DateTime'] = pd.to_datetime(df1['Date'] + ' ' + df1['Time'])

quiz_entries = df1[df1['Event'] == 'Quiz Entry']

hours, minutes, seconds = map(int, args.time_limit.split(':'))
threshold = timedelta(hours=hours, minutes=minutes, seconds=seconds)

with open(file_path2, 'r') as file:
    submissions = yaml.safe_load(file)

submission_data = []
for key, submission in submissions.items():
    submitter_info = submission[':submitters'][0]
    created_at_str = submission[':created_at']
    
    created_at_str = str(created_at_str).split('.')[0].replace(' Z', '')
    created_at_dt = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    
    submission_data.append({
        'Name': submitter_info[':name'],
        'DateTime': created_at_dt
    })

df2 = pd.DataFrame(submission_data)

local_tz = get_localzone()

results = []
for _, row in quiz_entries.iterrows():
    name = row['User']
    quiz_entry_time = row['DateTime'].replace(tzinfo=local_tz).astimezone(timezone.utc)
    
    if name in df2['Name'].values:
        course_time = df2[df2['Name'] == name]['DateTime'].values[0]
        course_time = pd.Timestamp(course_time).to_pydatetime()
        
        if quiz_entry_time.tzinfo is None:
            quiz_entry_time = quiz_entry_time.replace(tzinfo=timezone.utc)
        if course_time.tzinfo is None:
            course_time = course_time.replace(tzinfo=timezone.utc)
        
        time_diff = course_time - quiz_entry_time
        if time_diff > threshold:
            results.append((name, time_diff))

results_df = pd.DataFrame(results, columns=['Name', 'Time Difference'])
results_df.to_csv('output.csv', index=False)

for result in results:
    print(f"{result[0]}: {result[1]}")
