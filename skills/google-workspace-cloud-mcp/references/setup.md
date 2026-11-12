# Setup: Google Workspace Cloud MCP

One-time setup by a Workspace super administrator. Every step is done in a
web console or by the GitHub workflow. Nothing runs on a personal computer and
no key file is created.

Time: about 30 minutes.

## 1. Google Cloud project

1. Create or pick a project in the Google Cloud console.
2. Enable these APIs: Cloud Run, Cloud Build, Artifact Registry, Secret
   Manager, IAM Service Account Credentials, Admin SDK, Gmail, Calendar,
   Drive, Tasks, People.

## 2. Service account (no key)

1. IAM, Service Accounts, Create. Name it `gws-mcp`.
2. Do not create a key. The server asks Google to sign for it.
3. Open the account and copy its Unique ID (a 21-digit number).

## 3. Let the service sign as itself

On the `gws-mcp` service account, Permissions, Grant access:

- Principal: the `gws-mcp` account itself.
- Role: Service Account Token Creator.

## 4. Domain-wide delegation

Google Admin console, Security, API controls, Domain-wide delegation, Add new.

- Client ID: the Unique ID from step 2.
- Scopes, one line, comma separated:

```
https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/gmail.send,https://www.googleapis.com/auth/calendar.readonly,https://www.googleapis.com/auth/calendar,https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/tasks.readonly,https://www.googleapis.com/auth/contacts.readonly,https://www.googleapis.com/auth/admin.directory.user.readonly,https://www.googleapis.com/auth/admin.directory.user,https://www.googleapis.com/auth/admin.directory.group.readonly,https://www.googleapis.com/auth/admin.directory.group,https://www.googleapis.com/auth/admin.directory.orgunit.readonly,https://www.googleapis.com/auth/admin.reports.audit.readonly,https://www.googleapis.com/auth/admin.reports.usage.readonly
```

A read-only trial: leave out `gmail.modify`, `calendar`, `drive`,
`admin.directory.user` and `admin.directory.group`. Keep `gmail.send`; the
server uses it to email access requests. The administrator write tools then
return a scope error and change nothing.

## 5. Google sign-in client

Google Cloud console, APIs and Services, Credentials, Create OAuth client ID.

- Type: Web application.
- Authorised redirect URI: `https://<service-url>/auth/callback` (add it after
  the first deploy shows the URL).
- OAuth consent screen: User type Internal. Only company accounts can sign in.

## 6. Two secrets in Secret Manager

| Secret name | Value |
|---|---|
| `gws-mcp-google-client-secret` | The client secret from step 5 |
| `gws-mcp-jwt-key` | 64 random characters. Generate it in Cloud Shell. |

Grant the `gws-mcp` account the Secret Manager Secret Accessor role on both.
Do not paste either value into chat, a file or the repository.

## 7. Deploy from GitHub

The workflow `.github/workflows/gws-cloud-mcp.yml` deploys with Workload
Identity Federation. Set these repository variables (Settings, Secrets and
variables, Actions, Variables). None is a secret.

| Variable | Value |
|---|---|
| `GCP_PROJECT` | Project ID |
| `GCP_REGION` | For example `us-central1` |
| `GCP_WIF_PROVIDER` | Full name of the Workload Identity provider |
| `GCP_DEPLOY_SA` | Service account the workflow deploys as |
| `GWS_RUNTIME_SA` | Email of the `gws-mcp` account |
| `GWS_GOOGLE_CLIENT_ID` | Client ID from step 5 |
| `GWS_PRIMARY_DOMAIN` | The company domain |
| `GWS_ADMIN_EMAILS` | Administrator sign-in emails, comma separated |
| `GWS_DELEGATION_SUBJECT` | One super administrator email, used for Directory calls and system mail |
| `GWS_PUBLIC_URL` | The service URL. Leave empty for the first run. |

Then: Actions, gws-cloud-mcp, Run workflow.

1. The first run prints the service URL.
2. Set `GWS_PUBLIC_URL` to that URL and add the redirect URI in step 5.
3. Run the workflow again.

## 8. Check

1. Open `https://<service-url>/readyz`. Every value is `true`, and
   `admins_configured` is 1 or more.
2. Add the connector `https://<service-url>/mcp` in Claude and sign in as an
   administrator.
3. Call `workspace_connection_check`. Each source reports `ok`, or names the
   scope to add in step 4.

## Settings

| Setting | Required | Meaning |
|---|---|---|
| `PUBLIC_URL` | Yes | The service URL, no trailing slash |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Yes | The sign-in client from step 5 |
| `JWT_SIGNING_KEY` | Yes | Signs every token. 32 characters or more. |
| `PRIMARY_DOMAIN` | Yes | Accounts in this domain may sign in |
| `ADMIN_EMAILS` | Yes | Accounts with read, write and delete |
| `ADMIN_EMAIL` | Yes | Super administrator the server acts as for Directory calls and system mail |
| `SERVICE_ACCOUNT_EMAIL` | No | Set only when the delegated account differs from the runtime identity |
| `TASK_PROFILES` | No | JSON. Tasks that get a grant with no approval. |
| `TOKEN_EPOCH` | No | Unix time. Tokens issued earlier stop working. |
| `CF_ACCOUNT_ID`, `CF_DATABASE_ID`, `CF_API_TOKEN` | No | Cloudflare D1 for the optional knowledge base |

`TASK_PROFILES` example:

```json
{
  "schedule-coordination": {"perms": ["calendar.read"], "targets": ["*"], "ttl": 28800,
                            "description": "Find meeting times across the team."},
  "project-history": {"perms": ["kb.read"], "targets": ["*"], "ttl": 14400,
                      "description": "Read recorded project activity."}
}
```

## Optional knowledge base

The history tools need a Cloudflare D1 database and a scheduled Cloud Run job.

1. Create a D1 database in the Cloudflare dashboard. Run `schema.sql` in its
   console.
2. Store the D1 API token in Secret Manager as `gws-mcp-cf-token`.
3. Set the variables `GWS_CF_ACCOUNT_ID` and `GWS_CF_DATABASE_ID`.
4. Run the workflow with `deploy_harvester` ticked. It creates the job
   `gws-mcp-harvester` from the same image.
5. Cloud Scheduler: create a trigger that runs the job twice a day.

## Rotate and revoke

| Need | Action |
|---|---|
| Sign one person out | Suspend the account in Google. Access ends within 1 hour. |
| Remove an administrator | Remove the email from `GWS_ADMIN_EMAILS`, redeploy. Effect is immediate after deploy. |
| Sign everyone out | Set `TOKEN_EPOCH` to the current Unix time, redeploy. |
| Rotate the signing key | Add a new version of `gws-mcp-jwt-key`, redeploy. Every token and grant ends. |
