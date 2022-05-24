#!/bin/bash

protoc --proto_path=proto --python_out=build/gen proto/bakdata/corporate/v1/utils.proto proto/bakdata/corporate/v1/announcement.proto proto/bakdata/corporate/v1/person.proto proto/bakdata/corporate/v1/institution.proto
