# Deploying coha-gcloud to Google Cloud Run

The app was developed on Linux but can be deployed from Windows or Mac.

## Prerequisites

1. Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)
2. Authenticate:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   gcloud config set account YOUR_GOOGLE_ACCOUNT
   gcloud auth application-default set-quota-project YOUR_PROJECT_ID
   ```
   Example:
   ```bash
   gcloud config set project wildresearch-coha
   gcloud config set account harvey.dueck@gmail.com
   ```

## First-time setup

### 3. Create a GCP project

In the Google Cloud console, create a project (e.g. `wildresearch-coha`).

### 4. Create a Cloud Storage bucket

- Create a bucket to hold observation data (e.g. `coha-data`).
  If you use a name other than `coha-data`, set the `COHA_BUCKET_NAME`
  environment variable on the Cloud Run service (see step 9).
- Make the bucket **publicly readable** so the `/data` endpoint can serve direct
  download links:
  ```bash
  gsutil mb -p YOUR_PROJECT_ID -l YOUR_REGION gs://YOUR_BUCKET_NAME
  gsutil iam ch allUsers:objectViewer gs://YOUR_BUCKET_NAME
  ```
  Example:
  ```bash
  gsutil mb -p wildresearch-coha -l us-west1 gs://coha-data
  gsutil iam ch allUsers:objectViewer gs://coha-data
  ```

### 5. Initial deployment

From the directory containing `main.py`:
```bash
gcloud run deploy coha-gcloud --source . --region YOUR_REGION
```
- Allow unauthenticated invocations when prompted (the app is public).
- The CLI will suggest `coha-gcloud` as the service name.
- The original deployment uses region `us-west1` (Oregon) as the closest option
  to Vancouver.

### 6. Find the service URL

In the Cloud Run console, click the service name to find its URL:
```
https://coha-gcloud-<hash>.YOUR_REGION.run.app
```

### 7. Map a custom domain (optional but recommended)

- Ask your DNS administrator to add a CNAME record:
  ```
  YOUR_HOSTNAME. 3600 IN CNAME ghs.googlehosted.com.
  ```
  Example: `coha.pacificloon.ca. 3600 IN CNAME ghs.googlehosted.com.`
- Follow the [Cloud Run custom domain instructions](https://cloud.google.com/run/docs/mapping-custom-domains#run)
  to map your hostname to the service.

### 8. Create a Google Maps API key

The map won't work without one.

- Go to [Google Maps Platform](https://console.cloud.google.com/) → APIs & Services →
  Credentials → Create credentials → API key.
- Restrict the key to your custom domain as the HTTP referrer. Use the **bare
  domain** without `https://` (e.g. `coha.pacificloon.ca`) — this matches all
  paths automatically. Including the `https://` prefix will only match the exact
  root URL.
- Enable at minimum the **Maps JavaScript API** for your project. Other APIs
  (Distance Matrix, Geocoding, Geolocation, Maps Embed, Maps Static) may also be
  needed depending on future features.

### 8b. Create a Google Maps Map ID

Required for `AdvancedMarkerElement` support on the `/map` endpoint.

- In the Cloud Console: View All Products → Google Maps Platform → Map Management →
  Create map ID.
- Set type to **JavaScript**, style to **Vector**. Leave Tilt and Rotation unticked.
- Note the Map ID value for the next step.

### 9. Set environment variables

```bash
gcloud run services update coha-gcloud \
  --region YOUR_REGION \
  --set-env-vars COHA_MAPS_API_KEY=YOUR_MAPS_API_KEY,\
COHA_GOOGLE_MAP_ID=YOUR_MAP_ID,\
COHA_GCP_PROJECT_ID=YOUR_PROJECT_ID
```

Set the admin password **separately** using single quotes, which prevent the shell
from misinterpreting special characters:
```bash
gcloud run services update coha-gcloud \
  --region YOUR_REGION \
  --set-env-vars 'COHA_ADMIN_PASSWORD=YOUR_ADMIN_PASSWORD'
```

If you used a bucket name other than `coha-data`:
```bash
gcloud run services update coha-gcloud \
  --region YOUR_REGION \
  --set-env-vars COHA_BUCKET_NAME=YOUR_BUCKET_NAME
```

Full list of environment variables:

| Variable | Required | Description |
|---|---|---|
| `COHA_MAPS_API_KEY` | Yes | Google Maps JavaScript API key |
| `COHA_GOOGLE_MAP_ID` | Yes | Google Maps Map ID (for AdvancedMarkerElement) |
| `COHA_GCP_PROJECT_ID` | Yes | GCP project ID (e.g. `wildresearch-coha`) |
| `COHA_ADMIN_PASSWORD` | Yes | Password for the `/admin/` endpoint (HTTP Basic Auth) |
| `COHA_BUCKET_NAME` | No | GCS bucket name (default: `coha-data`) |

### 10. Deploy the app with env vars active

```bash
gcloud run deploy coha-gcloud --source . --region YOUR_REGION
```

Confirm the environment variables appear in the latest revision in the Cloud Run
console.

### 11. Test the app

- `/` — the survey form loads; the map shows station markers; GPS location works.
  Fill in all fields and submit the form to save a test observation — do not call
  `/save/` directly, as it requires a properly constructed form POST.
- `/map/` — the map shows the test observation you just submitted.
- `/data/` — download links are present and the CSV files open correctly.
- `/admin/` — log in with the admin password, view the test observation, then
  delete it to confirm the delete and summary update work correctly.

---

## Subsequent deployments

```bash
gcloud auth application-default login   # if credentials have expired
gcloud run deploy coha-gcloud --source . --region YOUR_REGION
```

---

## Setting up a test deployment

To test changes without affecting production data:

1. Create a separate bucket and seed it with production data:
   ```bash
   gsutil mb -p YOUR_PROJECT_ID -l YOUR_REGION gs://YOUR_TEST_BUCKET
   gsutil iam ch allUsers:objectViewer gs://YOUR_TEST_BUCKET
   gsutil -m cp "gs://YOUR_BUCKET_NAME/[A-X].*.csv" gs://YOUR_TEST_BUCKET/
   gsutil -m cp "gs://YOUR_BUCKET_NAME/COHA-data-*.csv" gs://YOUR_TEST_BUCKET/
   ```

2. Deploy a separate service:
   ```bash
   gcloud run deploy coha-gcloud-test --source . --region YOUR_REGION
   ```
   Allow unauthenticated invocations when prompted.

3. Grant public access (if the prompt was skipped):
   ```bash
   gcloud run services add-iam-policy-binding coha-gcloud-test \
     --region YOUR_REGION --member="allUsers" --role="roles/run.invoker"
   ```

4. Set environment variables, pointing at the test bucket:
   ```bash
   gcloud run services update coha-gcloud-test \
     --region YOUR_REGION \
     --set-env-vars COHA_BUCKET_NAME=YOUR_TEST_BUCKET,\
   COHA_GCP_PROJECT_ID=YOUR_PROJECT_ID,\
   COHA_MAPS_API_KEY=YOUR_MAPS_API_KEY,\
   COHA_GOOGLE_MAP_ID=YOUR_MAP_ID
   gcloud run services update coha-gcloud-test \
     --region YOUR_REGION \
     --set-env-vars 'COHA_ADMIN_PASSWORD=YOUR_TEST_PASSWORD'
   ```

5. Add the test service URL to the Maps API key's allowed referrers in the
   Google Cloud Console. Use the bare domain without `https://`.

6. When done, tear down the test service:
   ```bash
   gcloud run services delete coha-gcloud-test --region YOUR_REGION
   ```

---

## Admin interface

The `/admin/` endpoint is protected by HTTP Basic Auth. Any username is accepted;
only the password (set via `COHA_ADMIN_PASSWORD`) is checked. Use any browser —
it will prompt for credentials automatically.

To change the admin password:
```bash
gcloud run services update coha-gcloud \
  --region YOUR_REGION \
  --set-env-vars 'COHA_ADMIN_PASSWORD=YOUR_NEW_PASSWORD'
```

Always use single quotes around the password value to prevent the shell from
misinterpreting special characters.
