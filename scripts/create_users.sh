#!/bin/bash

URL="http://localhost/auth/register"

users=(
  test
  john
  alex
  mark
  ann
  frank
  sam
  george
  julia
  karen
  ivan
  mary
)

for user in "${users[@]}"; do
  curl -s -F "username=${user}" -F "password=${user}" "${URL}"
done
