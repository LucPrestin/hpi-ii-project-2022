#!/bin/bash

protoc --proto_path=proto --python_out=build/gen proto/bakdata/corporate/v1/utils.proto proto/bakdata/corporate/v1/announcement.proto proto/bakdata/corporate/v1/person.proto proto/bakdata/corporate/v1/institution.proto

for filename in ./build/gen/bakdata/corporate/v1/*.py; do
    [ -e "$filename" ] || continue

    sed -i 's/from bakdata/from build.gen.bakdata/gI' $filename
done
