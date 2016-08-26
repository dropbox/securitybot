## Splunk
A plugin for Splunk in the form of a custom application.
When installed, this app createes a new alerting action called "Send bot alerts" that sends alerts to Securitybot, creates a custom lookup that can find alerts from the database, and installs several macros that can be used to easily work with the bot.

### Alert actions
The "Send bot alerts" action can be added to any Splunk alert to send alerts to the bot.
However, the alert needs a little extra fine tuning before it's ready to go.
Every alert needs to output the following fields:
1. `hash`: A unique hash that identifies the alert.
2. `ldap`: The username of the user to send the alert to, ideally whoever caused the event.
3. `event_info`: A friendly explanation of what happened to be displayed to someone using the bot.
The alert action will also ask for a title field which will be displayed to the user as the title of the alert that went off.

### Macros
We have three macros that make generating hashes and later incorporating bot responses into alert rollups easier.
1. `securitybot_hashes`: Generates a `hash` field for every event.
   This should be added to a search immediately after the main search query as weird things happen otherwise.
2. `securitybot_squash_hashes(1)`: Compresses `values(hash)` or `list(hash)` into just one field.
   The parameter should be the name of the field to "squash".
   The send bot alerts alert action expects only a single hash, so we simply choose one if we've aggregated our events using `stats`.
3. `securitybot_responses`: Gather responses from bot alerts.
   When put right after the main query in a search generates fields `comment`, `performed`, and `authenticated`, which are the user's comment about an action, whether or not they performed and action, and whehter or not they successfully completed 2FA.

### Lookups
This addes the `securitybot` lookup which allows you to query the Securitybot database from within Splunk.
The fields in the lookup are `hash`, `comment`, `performed`, `authenticated`.
