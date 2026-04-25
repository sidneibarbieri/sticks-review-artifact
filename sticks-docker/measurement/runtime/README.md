# Docker Runtime Scratch

This directory holds workspace-local runtime copies created by the optional full
Docker replay.

Rules:

- Everything here is scratch and must stay out of release archives.
- The prepared Docker context keeps the frozen artifact immutable while allowing
  local runtime repairs such as executable-bit restoration.
- The context is recreated as needed by
  `sticks-docker/measurement/scripts/prepare_docker_runtime_context.py`.
