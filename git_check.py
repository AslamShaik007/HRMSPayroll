
# if __name__ == "__main__":
#     try:
#         from commits_get import *
#         import os
#         import subprocess

#         remote_commit = remote_commit_func()
#         # print("remote_commit",remote_commit)

#         local_commit = local_commit_func()
#         # print("local commit", local_commit)

#         if remote_commit != local_commit:
            
#             # subprocess.run("git pull", input = "ATBBx8zk9S3LbrzKnUNJhwsdD3uj6531A3CA", text=True, shell=True, capture_output=True) #need to remove this and do by ssh key-gen
#             # g = git.cmd.Git("/var/www/html/hrms")
#             # g.pull()

#             os.system("pip3 install -r /var/www/html/hrms/src/ubuntu_requirements_lts.txt")
#             os.system("python3 /var/www/html/hrms/src/manage.py migrate --settings=HRMSProject.settings.prod")
#             os.system("sudo systemctl restart gunicorn")
#     except Exception as e:
#         print("error in executing", e)