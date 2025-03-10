"""
karapace - schema registry authentication and authorization tests

Copyright (c) 2023 Aiven Ltd
See LICENSE for details
"""

import asyncio
from urllib.parse import quote

import aiohttp

from karapace.core.kafka.admin import KafkaAdminClient
from karapace.core.schema_models import SchemaType, ValidatedTypedSchema
from tests.integration.utils.rest_client import RetryRestClient
from tests.utils import (
    new_random_name,
    new_topic,
    schema_avro_json,
    schema_jsonschema_json,
    test_objects_avro,
    wait_for_topics,
)

NEW_TOPIC_TIMEOUT = 10

admin = aiohttp.BasicAuth("admin", "admin")
aladdin = aiohttp.BasicAuth("aladdin", "opensesame")
reader = aiohttp.BasicAuth("reader", "secret")


async def test_sr_auth(registry_async_retry_client_auth: RetryRestClient) -> None:
    subject = new_random_name("cave-")

    res = await registry_async_retry_client_auth.post(
        f"subjects/{quote(subject)}/versions", json={"schema": schema_avro_json}, expected_response_code=401
    )
    assert res.status_code == 401

    res = await registry_async_retry_client_auth.post(
        f"subjects/{quote(subject)}/versions", json={"schema": schema_avro_json}, auth=aladdin
    )
    assert res.status_code == 200
    sc_id = res.json()["id"]
    assert sc_id >= 0

    res = await registry_async_retry_client_auth.get(
        f"subjects/{quote(subject)}/versions/latest", expected_response_code=401
    )
    assert res.status_code == 401
    res = await registry_async_retry_client_auth.get(f"subjects/{quote(subject)}/versions/latest", auth=aladdin)
    assert res.status_code == 200
    assert sc_id == res.json()["id"]
    assert ValidatedTypedSchema.parse(SchemaType.AVRO, schema_avro_json) == ValidatedTypedSchema.parse(
        SchemaType.AVRO, res.json()["schema"]
    )


async def test_sr_auth_endpoints(registry_async_retry_client_auth: RetryRestClient) -> None:
    """Test endpoints for authorization"""

    subject = new_random_name("any-")

    res = await registry_async_retry_client_auth.post(
        f"compatibility/subjects/{quote(subject)}/versions/1",
        json={"schema": schema_avro_json},
        expected_response_code=401,
    )
    assert res.status_code == 401

    res = await registry_async_retry_client_auth.get(f"config/{quote(subject)}", expected_response_code=401)
    assert res.status_code == 401

    res = await registry_async_retry_client_auth.put(
        f"config/{quote(subject)}",
        json={"compatibility": "NONE"},
        expected_response_code=401,
    )
    assert res.status_code == 401

    res = await registry_async_retry_client_auth.get("config", expected_response_code=401)
    assert res.status_code == 401

    res = await registry_async_retry_client_auth.put("config", json={"compatibility": "NONE"}, expected_response_code=401)
    assert res.status_code == 401

    res = await registry_async_retry_client_auth.get("schemas/ids/1/versions", expected_response_code=401)
    assert res.status_code == 401

    # This is an exception that does not require authorization
    res = await registry_async_retry_client_auth.get("schemas/types")
    assert res.status_code == 200

    # but let's verify it answers normally if sending authorization header
    res = await registry_async_retry_client_auth.get("schemas/types", auth=admin)
    assert res.status_code == 200

    res = await registry_async_retry_client_auth.post(
        f"subjects/{quote(subject)}/versions", json={"schema": schema_avro_json}, expected_response_code=401
    )
    assert res.status_code == 401

    res = await registry_async_retry_client_auth.delete(f"subjects/{quote(subject)}/versions/1", expected_response_code=401)
    assert res.status_code == 401

    res = await registry_async_retry_client_auth.get(
        f"subjects/{quote(subject)}/versions/1/schema", expected_response_code=401
    )
    assert res.status_code == 401

    res = await registry_async_retry_client_auth.get(
        f"subjects/{quote(subject)}/versions/1/referencedby", expected_response_code=401
    )
    assert res.status_code == 401

    res = await registry_async_retry_client_auth.delete(f"subjects/{quote(subject)}", expected_response_code=401)
    assert res.status_code == 401

    res = await registry_async_retry_client_auth.get("mode", expected_response_code=401)
    assert res.status_code == 401

    res = await registry_async_retry_client_auth.get(f"mode/{quote(subject)}", expected_response_code=401)
    assert res.status_code == 401


async def test_sr_list_subjects(registry_async_retry_client_auth: RetryRestClient) -> None:
    cavesubject = new_random_name("cave-")
    carpetsubject = new_random_name("carpet-")

    res = await registry_async_retry_client_auth.post(
        f"subjects/{quote(cavesubject)}/versions", json={"schema": schema_avro_json}, auth=aladdin
    )
    assert res.status_code == 200
    sc_id = res.json()["id"]
    assert sc_id >= 0

    res = await registry_async_retry_client_auth.post(
        f"subjects/{quote(carpetsubject)}/versions", json={"schema": schema_avro_json}, auth=admin
    )
    assert res.status_code == 200

    res = await registry_async_retry_client_auth.get("subjects", auth=admin)
    assert res.status_code == 200
    assert [cavesubject, carpetsubject] == res.json()

    res = await registry_async_retry_client_auth.get(f"subjects/{quote(carpetsubject)}/versions", expected_response_code=401)
    assert res.status_code == 401

    res = await registry_async_retry_client_auth.get(f"subjects/{quote(carpetsubject)}/versions", auth=admin)
    assert res.status_code == 200
    assert [sc_id] == res.json()

    res = await registry_async_retry_client_auth.get("subjects", auth=aladdin)
    assert res.status_code == 200
    assert [cavesubject] == res.json()

    res = await registry_async_retry_client_auth.get(
        f"subjects/{quote(carpetsubject)}/versions", auth=aladdin, expected_response_code=403
    )
    assert res.status_code == 403

    res = await registry_async_retry_client_auth.get("subjects", auth=reader)
    assert res.status_code == 200
    assert [carpetsubject] == res.json()

    res = await registry_async_retry_client_auth.get(f"subjects/{quote(carpetsubject)}/versions", auth=reader)
    assert res.status_code == 200
    assert [1] == res.json()


async def test_sr_ids(registry_async_retry_client_auth: RetryRestClient) -> None:
    cavesubject = new_random_name("cave-")
    carpetsubject = new_random_name("carpet-")

    res = await registry_async_retry_client_auth.post(
        f"subjects/{quote(cavesubject)}/versions", json={"schema": schema_avro_json}, auth=aladdin
    )
    assert res.status_code == 200
    avro_sc_id = res.json()["id"]
    assert avro_sc_id >= 0

    res = await registry_async_retry_client_auth.post(
        f"subjects/{quote(carpetsubject)}/versions",
        json={"schemaType": "JSON", "schema": schema_jsonschema_json},
        auth=admin,
    )
    assert res.status_code == 200
    jsonschema_sc_id = res.json()["id"]
    assert jsonschema_sc_id >= 0

    res = await registry_async_retry_client_auth.get(f"schemas/ids/{avro_sc_id}", auth=aladdin)
    assert res.status_code == 200

    res = await registry_async_retry_client_auth.get(
        f"schemas/ids/{jsonschema_sc_id}", auth=aladdin, expected_response_code=404
    )
    assert res.status_code == 404
    assert {"error_code": 40403, "message": "Schema not found"} == res.json()

    res = await registry_async_retry_client_auth.get(f"schemas/ids/{avro_sc_id}", auth=reader, expected_response_code=404)
    assert res.status_code == 404
    assert {"error_code": 40403, "message": "Schema not found"} == res.json()

    res = await registry_async_retry_client_auth.get(f"schemas/ids/{jsonschema_sc_id}", auth=reader)
    assert res.status_code == 200


async def test_sr_auth_forwarding(
    registry_async_auth_pair: list[str], registry_async_retry_client_auth: RetryRestClient
) -> None:
    auth = aiohttp.BasicAuth("admin", "admin")

    # Test primary/replica forwarding with global config setting
    primary_url, replica_url = registry_async_auth_pair
    max_tries, counter = 5, 0
    wait_time = 0.5
    for compat in ["FULL", "BACKWARD", "FORWARD", "NONE"]:
        resp = await registry_async_retry_client_auth.put(f"{replica_url}/config", json={"compatibility": compat}, auth=auth)
        assert resp.ok
        while True:
            assert counter < max_tries, "Compat update not propagated"
            resp = await registry_async_retry_client_auth.get(f"{primary_url}/config", auth=auth)
            assert resp.ok
            data = resp.json()
            if "compatibilityLevel" not in data:
                counter += 1
                await asyncio.sleep(wait_time)
                continue
            if data["compatibilityLevel"] != compat:
                counter += 1
                await asyncio.sleep(wait_time)
                continue
            break


# Test that Kafka REST API works when configured with Schema Registry requiring authorization
async def test_rest_api_with_sr_auth(
    rest_async_client_registry_auth: RetryRestClient, admin_client: KafkaAdminClient
) -> None:
    client = rest_async_client_registry_auth

    topic = new_topic(admin_client, prefix="cave-rest-")
    await wait_for_topics(client, topic_names=[topic], timeout=NEW_TOPIC_TIMEOUT, sleep=1)

    payload = {"value_schema": schema_avro_json, "records": [{"value": o} for o in test_objects_avro]}
    res = await client.post(f"topics/{topic}", payload, headers={"Content-Type": "application/vnd.kafka.avro.v1+json"})
    assert res.ok
