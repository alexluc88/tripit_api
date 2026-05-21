tripit
======

A gem to help integrating with TripIt API. Please see the LICENSE for copyright information.

Overview
--------

The gem follows the typical oAuth process.

It uses consumer_key and consumer_secret which are provided by TripIt when you register your app in the [developer section](https://www.tripit.com/developer).

The first step of the process would be to get authorization from the specific user. set_host

To that end, we first get a [request token](#request) which is sort of an unauthorised token.

With that unauthorised token we redirect the user to the authorisation URL

` https://www.tripit.com/oauth/authorize?oauth_token=<oauth_token>&oauth_callback=<oauth_callback>`

The oauth_callback obviously only works for web application (no mobile).

Finally, when the application gets the control again, we get an [authorised token](#authorize) and make the [actual call](#actual)


Examples of use
---------------

### Installation


Add `tripit` to your Gemfile.

``` ruby
gem 'tripit', :git => "git://github.com/gonfva/tripit_api.git"
```
<a name="request">
### Obtain a request token

``` ruby
oauth_credential = TripIt::OAuthCredential.new(
    consumer_key, consumer_secret)
t = TripIt::API.new(oauth_credential, api_url)

request_token = t.get_request_token

print "request token:  #{request_token.token}\n"
print "request secret: #{request_token.token_secret}\n"
```
<a name="authorize">
### Obtain an authorized token

``` ruby
oauth_credential = TripIt::OAuthCredential.new(
    consumer_key, consumer_secret,
    request_token, request_token_secret)
t = TripIt::API.new(oauth_credential, api_url)

authorized_token = t.get_access_token

print "authorized token:  #{authorized_token.token}\n"
print "authorized secret: #{authorized_token.token_secret}\n"
```
<a name="actual">
### Actual requests

Get request (list of trips)

``` ruby
oauth_credential = TripIt::OAuthCredential.new(
    consumer_key, consumer_secret,
    authorized_token, authorized_token_secret)
t = TripIt::API.new(oauth_credential, api_url)
# print t.list.trip.to_xml.to_s

# Or with arguments
print t.list.trip({'include_objects' => 'true'}).to_xml.to_s
```

Post request (new trip)

``` ruby
trip_xml = "<Request><Trip>" \
           "<start_date>2009-12-09</start_date>" \
           "<end_date>2009-12-27</end_date>" \
           "<primary_location>New York, NY</primary_location>" \
           "</Trip></Request>"

oauth_credential = TripIt::OAuthCredential.new(
    consumer_key, consumer_secret,
    authorized_token, authorized_token_secret)

t = TripIt::API.new(oauth_credential, api_url)

puts t.create(trip_xml).to_xml.to_s
```



Additional documentation
------------------------

You can get more information from the [API site](http://tripit.github.io/api/doc/v1/index.html)

Claude skills
-------------

This repo also ships [Claude Code](https://claude.com/claude-code) skills under
`.claude/skills/`:

- **tripit** — an OAuth-signed CLI (`tripitcli`) that lets Claude read and edit
  your TripIt data (trips, reservations, points/rewards, profile). See
  `.claude/skills/tripit/SKILL.md`.
- **expertflyer-seat-alerts** — browser automation for ExpertFlyer seat alerts.

In Claude Code on the web these are auto-provisioned on session start; locally,
run the skill's `setup.sh`.

