# cjw-intercom-sink

Stream messages from a RabbitMQ queue to Intercom.

# Usage

Run `__main__.py` with environment variables:

* `CJW_RABBITMQ_HOST`: URL of RabbitMQ
* `CJW_INTERCOM_API_TOKEN`: API token for Intercom; or the magic string `mock`
* `CJW_INTERCOM_QUEUE_NAME`: RabbitMQ queue to read

Messages on the queue must be [msgpack](https://msgpack.org/index.html)-encoded
maps with the following keys:

* `method`: HTTP method (usually `POST`)
* `path`: HTTP path (e.g., `/contacts')
* `data`: Body of message (we'll encoded it as JSON)

This program will send messages, one at a time, and then ack the RabbitMQ
message.

## Mocking

Use the environment variable `CJW_INTERCOM_API_TOKEN=mock` to make this program
merely _log_ messages instead of sending them to Intercom. This is useful in
development and test environments.

# Error handling

On the Intercom side, this program adheres to [at-least
once](https://ably.com/blog/achieving-exactly-once-message-processing-with-ably)
semantics. We'll resend a request until we're certain Intercom
received it.

## RabbitMQ errors

If a message on the RabbitMQ queue is malformed, this program will log an error
and ack the message.

Otherwise, we only ack a message after it's been delivered to Intercom.

In the event of a RabbitMQ error, this program will crash. This should cause
the cluster to restart this service and resume sending the same, un-acked
message that was being sent previously. (TODO reconnect)

## Intercom errors

For each request, there is a "last response was 50X error" flag. Any retry
(except after 50X error) resets the flag to False.

In the event of *HTTP 429*, this program will pause according to [rate-limiting
rules](https://developers.intercom.com/intercom-api-reference/reference#rate-limiting)
and then retry.

In the event of *HTTP 404*, this program will log a *warning* but consider the
message successfully delivered. (An HTTP 404 can happen if we, say, try to
delete a contact we already deleted -- which is a natural thing to happen
with at-least-once semantics.)

In the event of *HTTP 50X*, this program will retry once with "last response was
50X error" flag set (as per [Intercom
docs](https://developers.intercom.com/intercom-api-reference/reference#http-responses).

In the event of *HTTP 40X* or a *second HTTP 50X*, this program will log an
*error* but consider the message successfully delivered. This indicates human
intervention is necessary; messages will be dropped so the queue doesn't back
up forever.

In the event of a *TCP error*, this program will log an error and retry.

# Developing

1. `docker build .` to make sure code is correctly formatted
2. Develop a new feature (and maybe add tests?)
3. `docker build .` to make sure it's still okay
4. `git push` to trigger a build

# Deploying

Use the Docker image, `gcr.io/workbenchdata-ci/cjw-intercom-sink:SHA1`

# License

MIT. See LICENSE.
