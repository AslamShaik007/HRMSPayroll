import requests
import json
import git

"""
######  NEEDS TO IMPLEMENT THIS WAY TO CHECK THE LATEST COMMIT IN REMOTE    ######

#bit bucket providing apis for various operations
#https://developer.atlassian.com/cloud/bitbucket/rest/api-group-commits/#api-repositories-workspace-repo-slug-commits-get



url = "https://api.bitbucket.org/2.0/repositories/psshrms/hrms/"


headers = {
  "Accept": "application/json",
  "Authorization": "Bearer <token>"
}

response = requests.request(
   "GET",
   url,
   headers=headers
)
print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))
"""



#HARD CODED WAY OF GETTING THE REMOTE LATEST COMMIT THIS FILE NEED TO BE REMOVED
def remote_commit_func():
    
  url = "https://bitbucket.org/!api/2.0/repositories/psshrms/hrms/refs/branches/staging"

  payload = {}
  headers = {
    'authority': 'bitbucket.org',
    'accept': 'application/json',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/json',
    'cookie': 'csrftoken=FVT3AnSCaBChpkaOvHkpQHtxx1OgYAM59ObedCB1MC4ihGyI5HvRzNE7igwCHdvX; ajs_anonymous_id=%225c787af9-68bb-4bc3-af7e-a13e8333a397%22; atlassian.account.xsrf.token=65d22fc0-dea9-45b9-9092-b6df4c952e62; _ga=GA1.2.496458535.1681131311; atlCohort={"bucketAll":{"bucketedAtUTC":"2023-04-10T12:56:27.615Z","version":"2","index":76,"bucketId":0}}; optimizelyEndUserId=oeu1681131389666r0.9549451608405748; atl_xid.ts=1681131392436; atl_xid.current=%5B%7B%22type%22%3A%22xc%22%2C%22value%22%3A%220684a3ae-ab46-40a2-b770-ba16b17f24cf%22%2C%22createdAt%22%3A%222023-04-10T12%3A56%3A32.418Z%22%7D%5D; atlUserHash=1393648548; OptanonConsent=landingPath=NotLandingPage&datestamp=Mon+Apr+17+2023+02%3A59%3A03+GMT%2B0530+(India+Standard+Time)&version=4.6.0&EU=false&groups=1%3A1%2C2%3A1%2C3%3A1%2C4%3A1%2C0_147330%3A1%2C0_155512%3A1%2C0_173487%3A1%2C0_173483%3A1%2C0_145889%3A1%2C0_173485%3A1%2C0_146517%3A1%2C0_144595%3A1%2C0_155516%3A1%2C0_155514%3A1%2C0_172277%3A1%2C0_155513%3A1%2C0_173486%3A1%2C0_162898%3A1%2C0_145888%3A1%2C0_173482%3A1%2C0_173484%3A1%2C0_144594%3A1%2C0_150453%3A1%2C0_173480%3A1%2C0_155515%3A1%2C101%3A1%2C117%3A1%2C120%3A1%2C144%3A1%2C160%3A1%2C180%3A1; _ga_MHPGQFJXWP=GS1.2.1689859747.4.0.1689859747.0.0.0; _gid=GA1.2.630860580.1693137911; _ga_BD58956NGD=GS1.2.1693176644.7.0.1693176644.0.0.0; JSESSIONID=AF4D11EA22E8B8F655EE40A70D075139; cloud.session.token=eyJraWQiOiJzZXNzaW9uLXNlcnZpY2VcL3Byb2QtMTU5Mjg1ODM5NCIsImFsZyI6IlJTMjU2In0.eyJhc3NvY2lhdGlvbnMiOltdLCJzdWIiOiI3MTIwMjA6NmY1ODczZGMtMzYxMi00OGU1LTlkZGUtNjg4MjQ1YWYyNzRjIiwiZW1haWxEb21haW4iOiJ2aXRlbGdsb2JhbC5jb20iLCJpbXBlcnNvbmF0aW9uIjpbXSwiY3JlYXRlZCI6MTY4MTEzMTM1OCwicmVmcmVzaFRpbWVvdXQiOjE2OTMxNzcyNDgsInZlcmlmaWVkIjp0cnVlLCJpc3MiOiJzZXNzaW9uLXNlcnZpY2UiLCJzZXNzaW9uSWQiOiI5Njk1OWUzMS03ZGU1LTRiZGEtOGE2OS0zNDViNjAxMDY0MTUiLCJzdGVwVXBzIjpbXSwiYXVkIjoiYXRsYXNzaWFuIiwibmJmIjoxNjkzMTc2NjQ4LCJleHAiOjE2OTU3Njg2NDgsImlhdCI6MTY5MzE3NjY0OCwiZW1haWwiOiJhYmhpbmVzaEB2aXRlbGdsb2JhbC5jb20iLCJqdGkiOiI5Njk1OWUzMS03ZGU1LTRiZGEtOGE2OS0zNDViNjAxMDY0MTUifQ.EG2Mgal9jr0gqqYQzgSiTy4c1yORYNMM8qI6UAJvYo5-zz3Xmlv6mBXbZIhbfy0BY-qrD6vNik8vUoUoOSvObAW9nxMoCRSaqyrR13XmuZs7NEJNfGPwByt1m4WtkOVET8RPr5KEqc_OsTYNg1ZBVxCzfqR6i6AahDaCfh6E-S7OeVGqPAC9iQAiwG9sW_RVPf1qDHg09LAKtRZFPWcgeK8LhJ-3dTjuFdqFiBGUqtvI8cJXwpS2lzGuMdqMq0c-XisUZctvCy_Jn30OudkVJE4U0GjchYn38P4EeXR6Xce6xceewzewBg4reNtELmniZcnGg-8WismFOl4GXuEIwA; cloud.session.token=eyJraWQiOiJzZXNzaW9uLXNlcnZpY2VcL3Byb2QtMTU5Mjg1ODM5NCIsImFsZyI6IlJTMjU2In0.eyJhc3NvY2lhdGlvbnMiOltdLCJzdWIiOiI3MTIwMjA6NmY1ODczZGMtMzYxMi00OGU1LTlkZGUtNjg4MjQ1YWYyNzRjIiwiZW1haWxEb21haW4iOiJ2aXRlbGdsb2JhbC5jb20iLCJpbXBlcnNvbmF0aW9uIjpbXSwiY3JlYXRlZCI6MTY4MTEzMTM1OCwicmVmcmVzaFRpbWVvdXQiOjE2OTMxODUzNTIsInZlcmlmaWVkIjp0cnVlLCJpc3MiOiJzZXNzaW9uLXNlcnZpY2UiLCJzZXNzaW9uSWQiOiI5Njk1OWUzMS03ZGU1LTRiZGEtOGE2OS0zNDViNjAxMDY0MTUiLCJzdGVwVXBzIjpbXSwiYXVkIjoiYXRsYXNzaWFuIiwibmJmIjoxNjkzMTg0NzUyLCJleHAiOjE2OTU3NzY3NTIsImlhdCI6MTY5MzE4NDc1MiwiZW1haWwiOiJhYmhpbmVzaEB2aXRlbGdsb2JhbC5jb20iLCJqdGkiOiI5Njk1OWUzMS03ZGU1LTRiZGEtOGE2OS0zNDViNjAxMDY0MTUifQ.r5J9sjwT7reapdLd4967vYlci5oZHJl4CLa9RAfZWmYRXreK99-c7Xt5LJDiKz9N25vjGeo6GpeVSmKvaJdx4_IxcnqCdTQDAJ_72g67mVK7_6v9lag2sVTpvWg8hUw1Ot6asIjYCLcuhy9_KIRp_A-QpN-Gb1hpH0JjZKrul30v767PIiKuhj4jIAeIfC3XNizTZp5Hgy8DO_xapNjvjy1XXaRnx7pcxewSVzHFhUFKQXdDdwTwjYvUAVxU7EGWA5YuQNzDYreSzgnk4EIcbPbGxC6VWhO5-C2GdeM2UN5yYBK1zaHBEcadI5gw98rO-cc7NlJR7LM1tQXOxMicfg',
    'if-none-match': '"gz[1f9108e9ccb1060ed8e8e36a45d9e1d2]"',
    'referer': 'https://bitbucket.org/psshrms/hrms/src/staging/',
    'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'x-bitbucket-frontend': 'frontbucket',
    'x-csrftoken': 'FVT3AnSCaBChpkaOvHkpQHtxx1OgYAM59ObedCB1MC4ihGyI5HvRzNE7igwCHdvX',
    'x-requested-with': 'XMLHttpRequest'
  }

  server_response = requests.request("GET", url, headers=headers, data=payload).text
  # print("response text from remote commit file",response.text)
  remote_commit = eval(server_response)['target']['hash']
  return remote_commit


def local_commit_func():
  local_repo_path = "/var/www/html/hrms/"
  branch_name = "staging"

  def get_latest_commit_version(local_repo_path, branch_name):
      repo = git.Repo(local_repo_path)
      try:
          branch = repo.heads[branch_name]
          latest_commit = branch.commit
          return latest_commit.hexsha
      except Exception as e:
          print(f"Error: {e}")
          return None

  latest_commit_hash = get_latest_commit_version(local_repo_path, branch_name)

  if latest_commit_hash:
      # print(f"Latest commit version: {latest_commit_hash}")
      ...
  else:
      # print("Unable to retrieve latest commit version.")
      ...

  return latest_commit_hash