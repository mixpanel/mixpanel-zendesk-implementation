# Basic Zendesk -> Mixpanel Implementation

The goal of this repo is to provide a basic workflow to send data from a running Zendesk implementation into Mixpanel, leveraging [Zendesk's Webhooks](https://support.zendesk.com/hc/en-us/articles/4408839108378-Creating-webhooks-in-Admin-Center)

## Workflow Outline

1. Create a webhook in Zendesk
2. Craft the data payload to send to Mixpanel's ingestion API
3. Create the triggers in Zendesk

## Creating the Zendesk Webhooks

[Zendesk webhooks](https://support.zendesk.com/hc/en-us/articles/4408839108378-Creating-webhooks-in-Admin-Center) can be used to send data payloads to specified external URLs

Start by creating 2 webhooks:
- One for ingesting event data, pointing to https://api.mixpanel.com/track
- One for ingesting profile data, pointing to https://api.mixpanel.com/engage

**Note:** :globe_with_meridians: The endpoints above point to Mixpanel's US data centers. If your project is set up for EU data residency, you will want to replace api.mixpanel.com with api-eu./mixpanel.com in both URLs :globe_with_meridians:

## Crafting the payload to send to Mixpanel

The next step is to create the format of the data that will be sent to Mixpanel in response to actions/changes on the tickets. The payloads will correspond to the profile updates + the following events:

- **Ticket Created:** event as the ticket is created with basic data on the requester and priority.

- **Ticket Updated:** event providing an update of the state of the ticket in specific parts of the lifecycle (ticket changing to pending, solved or closed).

- **Ticket Responded**: event when an agent has sent a public reply to the ticket.

The basic structure of a Mixpanel event follows the pattern below but more information about the API spec [can be found here](https://developer.mixpanel.com/reference/events):
```
{
    "event": "Ticket Created",
    "properties: {
        "token": "<YOUR_PROJECT_TOKEN>",
        "distinct_id": "123",
        "other_prop": "value",
        ...
    }
}
```

For this implementation, the distinct_id will be the ticket ID from Zendesk. You can also inject other properties like the organization of the end user as well as ticket category, status and so on. This can be done through [Zendesk placeholders](https://support.zendesk.com/hc/en-us/articles/4408887218330-Using-placeholders#topic_nfp_nja_vb).

An [example of the payload](sample_payloads/sample_ticket_created.json) for the Ticket Created event can be found in the [sample_payloads](sample_payloads) folder in this repo.

There is also a sample payload for updating the profile, which can be done every time the status of the ticket changes so you have a historical view of the state of the ticket in the events, and a current view in the profile.

## Creating the Zendesk Trigger

The last step would be to [create triggers](https://support.zendesk.com/hc/en-us/articles/4408886797466-Creating-triggers-for-automatic-ticket-updates-and-notifications) to notify the webhook and send the payload to Mixpanel. 

For the Ticket Created event, you can set the criteria to your specific Ticket Form from your implementation, and to be activated when the ticket is Created:

![Trigger activation criteria](/assets/images/trigger_conditions.png)

For the ticket Ticket Updated event, the criteria is similar, but using the Updated value instead of Created. Lastly, for Ticket Responded, the criteria would be the same, with the addition that the "comment" was public:

![Trigger activation criteria](/assets/images/trigger_event_responded.png)

For the profile update, since the idea is to update the state of the ticket at significant points, you can set the conditions to the ticket being created OR being set to pending/solved/closed.

## Optional: Fetching First Response, First Resolution and Full resolution Metrics

The events implemented will provide many metrics, but to be able to accurately track response times, you will want to get this data from Zendesk's API.

Within the [fetching_metrics](fetching_metrics) folder, you can leverage the python script to run on a cron (say once or twice a day). To set up the script, you will first want to get some basic authentication [credentials from Zendesk](https://developer.zendesk.com/api-reference/ticketing/introduction/#basic-authentication).

You will also need your Mixpanel's API secret and Project Token, which you can get through [project settings](https://help.mixpanel.com/hc/en-us/articles/115004490503).

Once you have both credentials, you will want to set them as environment variables for the script. In this example, they are created through the [run.sh](fetching_metrics/run.sh.txt) bash script, although if you are running this script in a web service like GCP's cloud functions or AWS lambda ones, you will have the ability to define the variables while creating the functions. The names for the variables can be found in the bash script.

Lastly, you will want to set the `lookup_hours` environment variable dependant on how frequently you will run the script. As an example, assuming you want to run the script to update the values once a day, you can set the value to 25 (25 hours), so every time it runs, it looks at the latest 25 hours worth of data, to have 1 hour of overlap just in case. If you run it twice a day, 13 hours would be the way to go, and so on.