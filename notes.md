# digital-technologies/notification-bus

Status: active — just created, nothing done yet
Unit: digital-technologies
Created: 2026-08-03

## Enviorment 


### Dynamis Information


Data Ingestion URI: https://ingest-dynamisps.centralus.kusto.windows.net

DataBase: Turbine_Hub_Data_2023

Table: Source(Folder)/DT35_MAIN


### Digital Technologies Information

Azure Subscription Details

Subscription Name: beusa-galaxy-qa-sub
Subscription ID: 4110066f-2622-4d19-8218-04709a26e593
Resource Group: RG_GalaxyQA-Orchestration

Service Bus Details

Service Bus Namespace: sb-qa-scus-5uhjokcqxur5g
Topic Name: power-azureiot-alert

The topic power-azureiot-alert is the topic we are planning to use for sending and receiving messages going forward.


Currently, the following topic is being used by the Galaxy application:

Current Topic: sbtgalscusqa03

## Scope

The plan is to produce a notification script/workflow that looks at my azure IOT and checks for a bool 0->1. Help me figure out the best way to configure that, and I would like to first make it work in a development enviorment. For now just doing booleans, in the future would like to consider analogs but this us just the MVP.  In the enviorment section above, another team has provided me with an dev enviorment that we will have to send our JSON to for notifications. 


Nice to haves:
1.) an easy way to add new notifications

For context in in folder, see what example JSON will look like to send to the notification bus 

## Deliverables






## Confirmed replay scope (2026-10-16)

Supersedes the original 0->1 assumption: 52G 1 is closed, 0 is open.
Detect 1->0 for all DT35_MAIN units, only qualifying when the previous
closed sample has NGGSEL >= 7000. Gaps over 5 seconds are uncertain.
First sample per unit is a baseline. Start with local historical replay
of the last 24 hours; defer JSON mapping, scheduling and sending.
