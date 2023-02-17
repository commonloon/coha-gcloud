# Deploying coha-gcloud to Google Cloud Run

I developed the flask app on Linux.  Here's what I remember about what's needed to get the app
to run correctly on Google Cloud Run. (*I'm Writing this from memory, so I've probably left out
important details, sorry.*)

TODO: Add links to the appropriate google cloud documentation

1. Install the google cloud command line tool
2. Authenticate the tool to the google account you want to use for the deployment
3. In the google cloud management console, reate a project to host the service.  I named my project "wildresearch-coha"
4. Create a cloud storage bucket to hold the data
   - I named my bucket coha-data.  You may have to use a different name: if so, you will need to change the value of STORAGE_BUCKET_NAME in main.py
   - configure the bucket to be publicly accessible.  The /data endpoint uses this public access to let users download data files.
     - If you don't want the bucket to be public, you will need to modify the /data endpoint to serve the data files directly
5. Do an initial deployment of the project, so you can get the URL that google will use to identify it
   - in the directory that contains main.py, run "gcloud run deploy --source ."  to deploy the project
     - you may have to set up some authentication stuff to make this work
     - the gcloud CLI will probably suggest coha-gcloud for the service name: that's what I used.
     - I put my service in region us-west1 (Oregon).  Other regions are fine, but Oregon seemed the closest option to Vancouver
6. Find the deployed coha-gcloud service in the Cloud Run console, then click on the service name to see details
   - The URL for the service should be deployed near the top of the page, beside the service name and region
   - The service URL will look something like this: https://coha-gcloud-5okgxs64sq-uw.a.run.app
7. Choose the domain name you want for the server, e.g. coha.pacificloon.ca
   - You can skip this step and just the service URL that google provides, but the long host name will make it more difficult for your users to access the site.
   - Follow the [instructions](https://cloud.google.com/run/docs/mapping-custom-domains#run) to map a custom domain to the cloud run app
      - Get whoever administers DNS for the domain to create a CNAME record that maps the desired hostname to ghs.google.com
        - e.g. coha.pacificloon.ca. 3600 IN CNAME ghs.googlehosted.com.
      - Use Cloud Run Domain Mappings to map the desired domain to the google cloud run service
8. Create a google maps API key
   - restrict the API key to required your custom domain as the referrer
   - restrict the API key to just the required Maps APIs.  You may need to enable the APIs on your project.
     - Distance Matrix API 
     - Geocoding API 
     - Geolocation API 
     - Maps Embed API 
     - **Maps JavaScript API** *this might be the only API you need*  
     - Maps Static API
9. Put the Maps API key into an environment variable for your coha-gcloud service
10. Deploy the app again and confirm that the environment variable exists in the latest revision
    - gcloud run deploy --source .
11. Test the app to make sure it serves pages and saves data
