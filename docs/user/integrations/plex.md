# Plex Integration Guide

## 1. Overview

The Plex integration enables bi-directional metadata sync, remote library scanning, playlist scrobbling, and stream monitoring between EchoSync and Plex Media Server instances.

## 2. Setup & Configuration

1. Obtain a Plex Auth Token via OAuth or direct account sign-in.
2. Register server URL and token in EchoSync Settings under Integrations.
3. Configure webhook targets in Plex pointing to `/api/webhooks/plex`.
