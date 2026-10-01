<script>
  import { onDestroy } from "svelte";
  import { createEventDispatcher } from "svelte";
  import apiClient from "../../api/client";
  import { feedback } from "../../stores/feedback";

  export let task = null;

  const dispatch = createEventDispatcher();

  let savingDraft = false;
  let approving = false;
  let rejecting = false;
  let autosavePending = false;
  let autosaveTimer = null;
  let initializedTaskId = null;
  let lastPersistedSignature = "";
  let lastObservedSignature = "";
  let metadataHistory = [];
  let restoringFromUndo = false;
  let showAdvanced = true;
  let isScanningAcoustID = false;
  let isLookingUpMB = false;
  let isLookingUpISRC = false;
  let isSimulatingPipeline = false;
  let pipelineDiagnostics = null;
  let showDiagnosticsDrawer = false;
  let lookupStatus = null; // { type: 'success'|'warning'|'error'|'info', message: string, timestamp: number }

  let showIsrcPrompt = false;
  let isrcInputValue = "";

  function openIsrcPrompt() {
    isrcInputValue = "";
    showIsrcPrompt = true;
  }

  function closeIsrcPrompt() {
    showIsrcPrompt = false;
  }

  let proposedMetadata = {
    title: "",
    edition: "",
    artist: "",
    album: "",
    year: "",
    track_number: "",
    disc_number: "",
    mbid: "",
    acoustid: "",
    acoustid_fingerprint: "",
    acoustid_fingerprint_duration: "",
    isrc: "",
    comments: "",
  };

  function normalizeUnknown(val) {
    if (!val || typeof val !== "string") return "";
    const lower = val.trim().toLowerCase();
    if (
      lower === "unknown artist" ||
      lower === "unknown title" ||
      lower === "unknown album"
    ) {
      return "";
    }
    return val;
  }

  $: if (task?.id && task.id !== initializedTaskId) {
    const proposed = task?.detected_metadata || {};

    proposedMetadata = {
      title:
        normalizeUnknown(proposed.title) ||
        normalizeUnknown(proposed.raw_title) ||
        "",
      edition:
        normalizeUnknown(proposed.edition) ||
        normalizeUnknown(proposed.version) ||
        "",
      artist:
        normalizeUnknown(proposed.artist) ||
        normalizeUnknown(proposed.artist_name) ||
        "",
      album:
        normalizeUnknown(proposed.album) ||
        normalizeUnknown(proposed.album_title) ||
        "",
      year: proposed.year || "",
      track_number: proposed.track_number || "",
      disc_number: proposed.disc_number || "",
      mbid: proposed.mbid || proposed.musicbrainz_id || "",
      acoustid: proposed.acoustid || proposed.acoustid_id || "",
      acoustid_fingerprint: proposed.acoustid_fingerprint || "",
      acoustid_fingerprint_duration:
        proposed.acoustid_fingerprint_duration || "",
      isrc: proposed.isrc || "",
      comments: proposed.comments || "",
    };

    const initialPayload = buildPayloadFrom(proposedMetadata);
    const initialSignature = JSON.stringify(initialPayload);
    metadataHistory = [initialPayload];
    lastObservedSignature = initialSignature;
    lastPersistedSignature = initialSignature;
    initializedTaskId = task.id;
    lookupStatus = null;
    pipelineDiagnostics = null;
    showDiagnosticsDrawer = false;
    clearAutosaveTimer();
    autosavePending = false;
  }

  $: proposedSignature = JSON.stringify(buildPayloadFrom(proposedMetadata));

  $: if (
    task?.id &&
    proposedSignature &&
    proposedSignature !== lastObservedSignature
  ) {
    if (!restoringFromUndo) {
      const snapshot = JSON.parse(proposedSignature);
      const previous = metadataHistory[metadataHistory.length - 1];
      if (!previous || JSON.stringify(previous) !== proposedSignature) {
        metadataHistory = [...metadataHistory, snapshot].slice(-50);
      }
    }

    lastObservedSignature = proposedSignature;
    queueAutosave();
  }

  $: currentMetadata =
    task?.current_metadata ||
    task?.source_metadata ||
    task?.raw_metadata ||
    task?.existing_metadata ||
    {};

  $: noTagsWarning =
    task?.detected_metadata &&
    !normalizeUnknown(task.detected_metadata.title) &&
    !normalizeUnknown(task.detected_metadata.artist) &&
    !normalizeUnknown(task.detected_metadata.raw_title) &&
    !normalizeUnknown(task.detected_metadata.artist_name);

  $: streamUrl = task?.id
    ? `/api/v1/core/metadata_review/${task.id}/stream`
    : "";
  $: coverUrl = task?.current_metadata?._has_embedded_cover
    ? `/api/v1/core/metadata_review/${task.id}/cover`
    : "";

  function getFilename(filePath) {
    if (!filePath) return "Unknown file";
    const normalized = String(filePath).replace(/\\/g, "/");
    const parts = normalized.split("/");
    return parts[parts.length - 1] || normalized;
  }

  function closeModal() {
    if (savingDraft || approving) {
      return;
    }
    dispatch("close");
  }

  function handleInputKeydown(event) {
    if (event.key !== "Enter") {
      return;
    }

    const target = event.target;
    const tagName = target?.tagName ? String(target.tagName).toLowerCase() : "";
    if (tagName !== "input") {
      return;
    }

    event.preventDefault();
    saveDraft();
  }

  function buildPayload() {
    return buildPayloadFrom(proposedMetadata);
  }

  function buildPayloadFrom(source) {
    return {
      title: (source.title || "").trim(),
      edition: (source.edition || "").trim(),
      artist: (source.artist || "").trim(),
      album: (source.album || "").trim(),
      year: source.year ? Number(source.year) || source.year : "",
      track_number: source.track_number
        ? Number(source.track_number) || source.track_number
        : "",
      disc_number: source.disc_number
        ? Number(source.disc_number) || source.disc_number
        : "",
      mbid: (source.mbid || "").trim(),
      acoustid: (source.acoustid || "").trim(),
      acoustid_fingerprint: (source.acoustid_fingerprint || "").trim(),
      acoustid_fingerprint_duration: source.acoustid_fingerprint_duration
        ? Number(source.acoustid_fingerprint_duration) ||
          source.acoustid_fingerprint_duration
        : "",
      isrc: (source.isrc || "").trim(),
      comments: (source.comments || "").trim(),
    };
  }

  function clearAutosaveTimer() {
    if (autosaveTimer) {
      clearTimeout(autosaveTimer);
      autosaveTimer = null;
    }
  }

  function queueAutosave() {
    if (!task?.id || savingDraft || approving) return;
    clearAutosaveTimer();
    autosavePending = true;
    autosaveTimer = setTimeout(() => {
      saveDraft({ silent: true });
    }, 1000);
  }

  const handleAutosave = queueAutosave;

  function undoLastChange() {
    if (metadataHistory.length < 2 || savingDraft || approving) {
      return;
    }

    const nextHistory = metadataHistory.slice(0, -1);
    const previousState = nextHistory[nextHistory.length - 1];
    metadataHistory = nextHistory;

    restoringFromUndo = true;
    proposedMetadata = {
      ...proposedMetadata,
      ...previousState,
    };
    restoringFromUndo = false;

    lastObservedSignature = JSON.stringify(buildPayloadFrom(proposedMetadata));
    queueAutosave();
  }

  async function saveDraft(options = {}) {
    const { silent = false } = options;
    if (!task?.id || savingDraft || approving) return;
    const payload = buildPayload();
    const payloadSignature = JSON.stringify(payload);

    if (payloadSignature === lastPersistedSignature && silent) {
      autosavePending = false;
      return;
    }

    savingDraft = true;
    dispatch("draftstart", { taskId: task.id });
    try {
      await apiClient.put(`/core/metadata_review/${task.id}`, {
        metadata: payload,
      });
      lastPersistedSignature = payloadSignature;
      if (!silent) {
        feedback.addToast("Draft metadata saved", "success");
      }
      dispatch("saved", { taskId: task.id, metadata: payload });
    } catch (error) {
      console.error("Failed to save draft:", error);
      feedback.addToast("Failed to save draft metadata", "error");
    } finally {
      savingDraft = false;
      autosavePending = false;
      dispatch("draftend", { taskId: task.id });
    }
  }

  async function approveAndImport() {
    if (!task?.id || approving) return;
    clearAutosaveTimer();
    approving = true;
    dispatch("approvestart", { taskId: task.id });
    try {
      const payload = buildPayload();
      await apiClient.post(
        `/core/metadata_review/${task.id}/approve`,
        { metadata: payload },
        { timeout: 60000 },
      );
      feedback.addToast("Metadata approved and file imported", "success");
      dispatch("approved", { taskId: task.id, metadata: payload });
      dispatch("close");
    } catch (error) {
      console.error("Failed to approve and import:", error);
      feedback.addToast(
        error?.response?.data?.detail || "Failed to approve and import file",
        "error",
      );
    } finally {
      approving = false;
      dispatch("approveend", { taskId: task.id });
    }
  }

  async function rejectAndDelete() {
    if (!task?.id || rejecting || approving || savingDraft) return;
    const filename = getFilename(task?.file_path);
    const confirmDelete = window.confirm(
      `Are you sure you want to reject this track and permanently delete the physical file from disk?\n\nFile: ${filename}`,
    );
    if (!confirmDelete) return;

    clearAutosaveTimer();
    rejecting = true;
    try {
      await apiClient.post(`/core/metadata_review/${task.id}/reject`);
      feedback.addToast("Track rejected and file deleted from disk", "success");
      dispatch("rejected", { taskId: task.id, item: task });
      dispatch("close");
    } catch (error) {
      console.error("Failed to reject and delete file:", error);
      feedback.addToast(
        error?.response?.data?.detail || "Failed to reject and delete file",
        "error",
      );
    } finally {
      rejecting = false;
    }
  }

  function displayValue(value) {
    if (value === undefined || value === null || value === "") {
      return "Not available";
    }
    return String(value);
  }

  onDestroy(() => {
    clearAutosaveTimer();
  });

  function applyMetadataUpdate(newMetadata) {
    if (!newMetadata || typeof newMetadata !== "object") {
      return { changed: false, fieldsChanged: [], nextState: proposedMetadata };
    }

    clearAutosaveTimer();

    const normalizedLookupMetadata = {
      ...newMetadata,
      title: newMetadata.title ?? proposedMetadata.title,
      edition:
        newMetadata.edition ?? newMetadata.version ?? proposedMetadata.edition,
      artist: newMetadata.artist ?? proposedMetadata.artist,
      album: newMetadata.album ?? proposedMetadata.album,
      year: newMetadata.year ?? newMetadata.date ?? proposedMetadata.year,
      track_number: newMetadata.track_number ?? proposedMetadata.track_number,
      disc_number: newMetadata.disc_number ?? proposedMetadata.disc_number,
      mbid:
        newMetadata.mbid ??
        newMetadata.musicbrainz_id ??
        newMetadata.recording_id ??
        proposedMetadata.mbid,
      acoustid:
        newMetadata.acoustid ??
        newMetadata.acoustid_id ??
        proposedMetadata.acoustid,
      acoustid_fingerprint:
        newMetadata.acoustid_fingerprint ??
        proposedMetadata.acoustid_fingerprint,
      acoustid_fingerprint_duration:
        newMetadata.acoustid_fingerprint_duration ??
        proposedMetadata.acoustid_fingerprint_duration,
      isrc: newMetadata.isrc ?? proposedMetadata.isrc,
      comments: newMetadata.comments ?? proposedMetadata.comments,
    };

    const nextState = {
      ...proposedMetadata,
      ...normalizedLookupMetadata,
      mbid: normalizedLookupMetadata.mbid || "",
      acoustid: normalizedLookupMetadata.acoustid || "",
      acoustid_fingerprint: normalizedLookupMetadata.acoustid_fingerprint || "",
      acoustid_fingerprint_duration:
        normalizedLookupMetadata.acoustid_fingerprint_duration || "",
      isrc: normalizedLookupMetadata.isrc || "",
    };

    const fieldsChanged = [];
    for (const key of [
      "title",
      "edition",
      "artist",
      "album",
      "year",
      "track_number",
      "disc_number",
      "mbid",
      "acoustid",
      "isrc",
    ]) {
      if (
        String(nextState[key] || "").trim() !==
        String(proposedMetadata[key] || "").trim()
      ) {
        fieldsChanged.push(key);
      }
    }

    proposedMetadata = nextState;
    queueAutosave();
    return { changed: fieldsChanged.length > 0, fieldsChanged, nextState };
  }

  function getLookupMetadata(response) {
    return (
      response?.data?.metadata ||
      response?.data?.detected_metadata ||
      response?.data?.task?.detected_metadata ||
      null
    );
  }

  async function runMusicBrainzLookup() {
    if (
      !task?.id ||
      isScanningAcoustID ||
      isLookingUpMB ||
      isLookingUpISRC ||
      savingDraft ||
      approving
    ) {
      return;
    }

    clearAutosaveTimer();
    isLookingUpMB = true;
    try {
      const response = await apiClient.post(
        `/core/metadata_review/${task.id}/lookup/musicbrainz`,
        {
          artist: (proposedMetadata.artist || "").trim(),
          title: (proposedMetadata.title || "").trim(),
        },
        { timeout: 60000 },
      );

      if (response?.data?.match_found === false) {
        const warnMsg =
          response?.data?.message ||
          "MusicBrainz: No matching record found in database.";
        lookupStatus = {
          type: "warning",
          message: warnMsg,
          timestamp: Date.now(),
        };
        pipelineDiagnostics = {
          winningStage: "Stage 5: MusicBrainz (No Match)",
          resolvedMetadata: {},
          diagnostics: [
            {
              stage: "Stage 5: Text Waterfall",
              status: "miss",
              message: warnMsg,
              candidates: [],
            },
          ],
        };
        feedback.addToast({
          type: "warning",
          message: warnMsg,
        });
        return;
      }

      const updatedMetadata = getLookupMetadata(response);
      if (updatedMetadata && response?.data?.match_found) {
        pipelineDiagnostics = {
          winningStage: "Stage 5: MusicBrainz Text Search",
          resolvedMetadata: updatedMetadata,
          diagnostics: [
            {
              stage: "Stage 5: Text Waterfall",
              status: "hit",
              message: `MusicBrainz catalog matched recording: "${updatedMetadata.title || "Track"}" by "${updatedMetadata.artist || "Artist"}"`,
              candidates: [
                {
                  mbid: updatedMetadata.mbid || updatedMetadata.musicbrainz_id,
                  title: updatedMetadata.title,
                  artist: updatedMetadata.artist,
                  status: "WINNER",
                  total_score: 90.0,
                  reason: "Text query matched MusicBrainz catalog recording",
                },
              ],
            },
          ],
        };

        const { changed, fieldsChanged } = applyMetadataUpdate(updatedMetadata);
        if (changed && fieldsChanged.length > 0) {
          const changedKeys = fieldsChanged.map((f) => f.replace("_", " "));
          const successMsg = `Matched! Updated: ${changedKeys.join(", ")}`;
          lookupStatus = {
            type: "success",
            message: successMsg,
            timestamp: Date.now(),
          };
          feedback.addToast({
            type: "success",
            message: `Match found! Updated: ${changedKeys.join(", ")}`,
          });
        } else {
          const infoMsg =
            "Match confirmed: Current metadata is already up to date.";
          lookupStatus = {
            type: "info",
            message: infoMsg,
            timestamp: Date.now(),
          };
          feedback.addToast({
            type: "info",
            message: infoMsg,
          });
        }
      } else if (!updatedMetadata) {
        const noRecordMsg =
          "MusicBrainz: No matching record found in database.";
        lookupStatus = {
          type: "warning",
          message: noRecordMsg,
          timestamp: Date.now(),
        };
        pipelineDiagnostics = {
          winningStage: "Stage 5: MusicBrainz (No Match)",
          resolvedMetadata: {},
          diagnostics: [
            {
              stage: "Stage 5: Text Waterfall",
              status: "miss",
              message: noRecordMsg,
              candidates: [],
            },
          ],
        };
        feedback.addToast({
          type: "warning",
          message: noRecordMsg,
        });
      }
    } catch (error) {
      console.error("MusicBrainz lookup failed:", error);
      let errMsg = "MusicBrainz lookup failed";
      if (
        error?.code === "ECONNABORTED" ||
        error?.message?.includes("timeout")
      ) {
        errMsg =
          "MusicBrainz lookup timed out after 60s. The service may be busy.";
      } else {
        const status = error?.response?.status;
        if (status === 404) {
          errMsg = "No matching records found";
        } else if (status === 500 || status === 503) {
          errMsg = "Provider lookup failed or is temporarily unavailable.";
        } else if (error?.response?.data?.detail) {
          errMsg = error.response.data.detail;
        }
      }
      lookupStatus = { type: "error", message: errMsg, timestamp: Date.now() };
      pipelineDiagnostics = {
        winningStage: "Stage 5: MusicBrainz (Error)",
        resolvedMetadata: {},
        diagnostics: [
          {
            stage: "Stage 5: Text Waterfall",
            status: "rejected",
            message: errMsg,
            candidates: [],
          },
        ],
      };
      feedback.addToast({
        type: "error",
        message: errMsg,
      });
    } finally {
      isLookingUpMB = false;
    }
  }

  async function runAcoustIDLookup() {
    if (
      !task?.id ||
      isScanningAcoustID ||
      isLookingUpMB ||
      isLookingUpISRC ||
      savingDraft ||
      approving
    ) {
      return;
    }

    clearAutosaveTimer();
    isScanningAcoustID = true;
    try {
      const response = await apiClient.post(
        `/core/metadata_review/${task.id}/lookup/acoustid`,
        {},
        { timeout: 60000 },
      );

      if (response?.data?.match_found === false) {
        const updatedMetadata = getLookupMetadata(response);
        if (updatedMetadata) {
          applyMetadataUpdate(updatedMetadata);
        }
        const noMatchMsg =
          "AcoustID: No acoustic fingerprint match found in database.";
        lookupStatus = {
          type: "warning",
          message: noMatchMsg,
          timestamp: Date.now(),
        };
        pipelineDiagnostics = {
          winningStage: "Stage 3: AcoustID (No Match)",
          resolvedMetadata: updatedMetadata || {},
          diagnostics: [
            {
              stage: "Stage 3: AcoustID",
              status: "miss",
              message: noMatchMsg,
              candidates: [],
            },
          ],
        };
        feedback.addToast({
          type: "warning",
          message: response?.data?.message || noMatchMsg,
        });
        return;
      }

      const updatedMetadata = getLookupMetadata(response);
      if (updatedMetadata && response?.data?.match_found) {
        const resResult = response.data?.resolution_result;
        pipelineDiagnostics = {
          winningStage: resResult?.resolution_stage || "Stage 3: AcoustID",
          resolvedMetadata: updatedMetadata,
          diagnostics:
            resResult?.diagnostics && resResult.diagnostics.length > 0
              ? resResult.diagnostics
              : [
                  {
                    stage: "Stage 3: AcoustID",
                    status: "hit",
                    message: `AcoustID matched: "${updatedMetadata.title || "Track"}" by "${updatedMetadata.artist || "Artist"}"`,
                    candidates: [
                      {
                        mbid:
                          updatedMetadata.mbid || updatedMetadata.musicbrainz_id,
                        title: updatedMetadata.title,
                        artist: updatedMetadata.artist,
                        status: "WINNER",
                        total_score: resResult?.confidence_score
                          ? resResult.confidence_score * 100
                          : 95.0,
                        reason:
                          "Acoustic fingerprint matched in AcoustID library",
                      },
                    ],
                  },
                ],
        };

        const { changed, fieldsChanged } = applyMetadataUpdate(updatedMetadata);
        if (changed && fieldsChanged.length > 0) {
          const changedKeys = fieldsChanged.map((f) => f.replace("_", " "));
          const successMsg = `Matched! Updated: ${changedKeys.join(", ")}`;
          lookupStatus = {
            type: "success",
            message: successMsg,
            timestamp: Date.now(),
          };
          feedback.addToast({
            type: "success",
            message: `Match found! Updated: ${changedKeys.join(", ")}`,
          });
        } else {
          const infoMsg =
            "Match confirmed: Current metadata is already up to date.";
          lookupStatus = {
            type: "info",
            message: infoMsg,
            timestamp: Date.now(),
          };
          feedback.addToast({
            type: "info",
            message: infoMsg,
          });
        }
      } else {
        const noMatchMsg =
          "AcoustID: No acoustic fingerprint match found in database.";
        lookupStatus = {
          type: "warning",
          message: noMatchMsg,
          timestamp: Date.now(),
        };
        pipelineDiagnostics = {
          winningStage: "Stage 3: AcoustID (No Match)",
          resolvedMetadata: {},
          diagnostics: [
            {
              stage: "Stage 3: AcoustID",
              status: "miss",
              message: noMatchMsg,
              candidates: [],
            },
          ],
        };
        feedback.addToast({
          type: "warning",
          message: noMatchMsg,
        });
      }
    } catch (error) {
      console.error("AcoustID lookup failed:", error);
      let errMsg = "AcoustID lookup failed";
      if (
        error?.code === "ECONNABORTED" ||
        error?.message?.includes("timeout")
      ) {
        errMsg = "AcoustID fingerprinting timed out.";
      } else {
        const status = error?.response?.status;
        if (status === 404) {
          errMsg = "No matching records found";
        } else if (status === 500 || status === 503) {
          errMsg = "Provider lookup failed or is temporarily unavailable.";
        } else if (error?.response?.data?.detail) {
          errMsg = error.response.data.detail;
        }
      }
      lookupStatus = { type: "error", message: errMsg, timestamp: Date.now() };
      pipelineDiagnostics = {
        winningStage: "Stage 3: AcoustID (Error)",
        resolvedMetadata: {},
        diagnostics: [
          {
            stage: "Stage 3: AcoustID",
            status: "rejected",
            message: errMsg,
            candidates: [],
          },
        ],
      };
      feedback.addToast({
        type: "error",
        message: errMsg,
      });
    } finally {
      isScanningAcoustID = false;
    }
  }

  async function runISRCLookup() {
    if (
      isScanningAcoustID ||
      isLookingUpMB ||
      isLookingUpISRC ||
      savingDraft ||
      approving
    ) {
      return;
    }
    openIsrcPrompt();
  }

  async function doRunISRCLookup(isrc) {
    if (
      isScanningAcoustID ||
      isLookingUpMB ||
      isLookingUpISRC ||
      savingDraft ||
      approving
    ) {
      return;
    }

    clearAutosaveTimer();
    isLookingUpISRC = true;
    try {
      const response = await apiClient.post(
        `/core/metadata_review/${task.id}/lookup/isrc`,
        { isrc },
        { timeout: 60000 },
      );

      if (response?.data?.match_found === false) {
        const noMatchMsg = "ISRC: No matching record found in database.";
        lookupStatus = {
          type: "warning",
          message: noMatchMsg,
          timestamp: Date.now(),
        };
        pipelineDiagnostics = {
          winningStage: "Stage 4: ISRC (No Match)",
          resolvedMetadata: {},
          diagnostics: [
            {
              stage: "Stage 4: ISRC",
              status: "miss",
              message: noMatchMsg,
              candidates: [],
            },
          ],
        };
        feedback.addToast({
          type: "warning",
          message: response?.data?.message || noMatchMsg,
        });
        return;
      }

      const updatedMetadata = getLookupMetadata(response);
      if (updatedMetadata && response?.data?.match_found) {
        pipelineDiagnostics = {
          winningStage: "Stage 4: ISRC Direct Match",
          resolvedMetadata: updatedMetadata,
          diagnostics: [
            {
              stage: "Stage 4: ISRC",
              status: "hit",
              message: `ISRC code ${isrc} resolved recording: "${updatedMetadata.title || "Track"}" by "${updatedMetadata.artist || "Artist"}"`,
              candidates: [
                {
                  mbid: updatedMetadata.mbid || updatedMetadata.musicbrainz_id,
                  title: updatedMetadata.title,
                  artist: updatedMetadata.artist,
                  status: "WINNER",
                  total_score: 100.0,
                  reason: `Exact ISRC code match (${isrc})`,
                },
              ],
            },
          ],
        };

        const { changed, fieldsChanged } = applyMetadataUpdate(updatedMetadata);
        if (changed && fieldsChanged.length > 0) {
          const changedKeys = fieldsChanged.map((f) => f.replace("_", " "));
          const successMsg = `Matched! Updated: ${changedKeys.join(", ")}`;
          lookupStatus = {
            type: "success",
            message: successMsg,
            timestamp: Date.now(),
          };
          feedback.addToast({
            type: "success",
            message: `Match found! Updated: ${changedKeys.join(", ")}`,
          });
        } else {
          const infoMsg =
            "Match confirmed: Current metadata is already up to date.";
          lookupStatus = {
            type: "info",
            message: infoMsg,
            timestamp: Date.now(),
          };
          feedback.addToast({
            type: "info",
            message: infoMsg,
          });
        }
      } else {
        const noMatchMsg = "ISRC: No matching record found in database.";
        lookupStatus = {
          type: "warning",
          message: noMatchMsg,
          timestamp: Date.now(),
        };
        pipelineDiagnostics = {
          winningStage: "Stage 4: ISRC (No Match)",
          resolvedMetadata: {},
          diagnostics: [
            {
              stage: "Stage 4: ISRC",
              status: "miss",
              message: noMatchMsg,
              candidates: [],
            },
          ],
        };
        feedback.addToast({
          type: "warning",
          message: noMatchMsg,
        });
      }
    } catch (error) {
      console.error("ISRC lookup failed:", error);
      let errMsg = "ISRC lookup failed";
      const status = error?.response?.status;
      if (status === 400) {
        errMsg = "Invalid ISRC format — expected 12 alphanumeric characters";
      } else if (status === 404) {
        errMsg = "No matching records found";
      } else if (status === 500 || status === 503) {
        errMsg = "Provider lookup failed or is temporarily unavailable.";
      } else if (error?.response?.data?.detail) {
        errMsg = error.response.data.detail;
      }
      lookupStatus = { type: "error", message: errMsg, timestamp: Date.now() };
      pipelineDiagnostics = {
        winningStage: "Stage 4: ISRC (Error)",
        resolvedMetadata: {},
        diagnostics: [
          {
            stage: "Stage 4: ISRC",
            status: "rejected",
            message: errMsg,
            candidates: [],
          },
        ],
      };
      feedback.addToast({
        type: "error",
        message: errMsg,
      });
    } finally {
      isLookingUpISRC = false;
    }
  }

  function submitIsrcPrompt() {
    const isrc = isrcInputValue.trim();
    if (!isrc) {
      feedback.addToast({
        type: "error",
        message: "Please enter an ISRC code",
      });
      return;
    }
    closeIsrcPrompt();
    doRunISRCLookup(isrc);
  }

  async function runFullPipelineSimulation() {
    if (
      !task?.id ||
      isSimulatingPipeline ||
      isScanningAcoustID ||
      isLookingUpMB ||
      isLookingUpISRC ||
      savingDraft ||
      approving
    ) {
      return;
    }

    clearAutosaveTimer();
    isSimulatingPipeline = true;
    try {
      const response = await apiClient.post(
        `/core/metadata_review/${task.id}/simulate-pipeline`,
        {},
        { timeout: 90000 },
      );

      if (response?.data?.status === "success") {
        const resMeta = response.data.resolved_metadata || {};
        const diagnostics = response.data.diagnostics || [];
        const winningStage = response.data.winning_stage || "Unknown";

        pipelineDiagnostics = {
          winningStage,
          resolvedMetadata: resMeta,
          diagnostics,
        };
        showDiagnosticsDrawer = true;

        const { changed, fieldsChanged } = applyMetadataUpdate(resMeta);
        if (changed && fieldsChanged.length > 0) {
          const changedKeys = fieldsChanged.map((f) => f.replace("_", " "));
          lookupStatus = {
            type: "success",
            message: `Simulation Complete (${winningStage})! Updated: ${changedKeys.join(", ")}`,
            timestamp: Date.now(),
          };
          feedback.addToast({
            type: "success",
            message: `Simulation Complete! Winning Stage: ${winningStage}`,
          });
        } else {
          lookupStatus = {
            type: "info",
            message: `Simulation Complete (${winningStage}). Metadata already matches winner.`,
            timestamp: Date.now(),
          };
          feedback.addToast({
            type: "info",
            message: `Simulation Complete! Winning Stage: ${winningStage}`,
          });
        }
      } else {
        feedback.addToast({
          type: "warning",
          message: response?.data?.detail || "Simulation returned no result",
        });
      }
    } catch (error) {
      console.error("Pipeline simulation failed:", error);
      const errMsg =
        error?.response?.data?.detail ||
        error?.message ||
        "Pipeline simulation failed";
      lookupStatus = {
        type: "error",
        message: errMsg,
        timestamp: Date.now(),
      };
      feedback.addToast({
        type: "error",
        message: errMsg,
      });
    } finally {
      isSimulatingPipeline = false;
    }
  }
</script>

<div
  class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
>
  <div
    class={`relative flex flex-col w-full ${showDiagnosticsDrawer ? "max-w-7xl" : "max-w-5xl"} max-h-[90vh] bg-slate-900 rounded-xl border border-slate-700 shadow-2xl overflow-hidden transition-all duration-300`}
  >
    <!-- 1. Header (Fixed Height) -->
    <header
      class="flex shrink-0 items-center justify-between p-4 border-b border-slate-800 bg-slate-900"
    >
      <div>
        <p
          class="text-xs uppercase tracking-wide text-cyan-300/80 font-semibold"
        >
          Metadata Editor
        </p>
        <h3 class="text-xl font-bold text-slate-100">Edit Metadata</h3>
        <p class="text-xs text-slate-400 mt-1">
          Task #{task?.id} - {getFilename(task?.file_path)}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg flex items-center gap-1.5 transition-colors border border-slate-700/60 {showDiagnosticsDrawer ? 'ring-1 ring-cyan-500/50 bg-slate-700 text-cyan-300' : ''}"
          on:click={() => (showDiagnosticsDrawer = !showDiagnosticsDrawer)}
        >
          <span>🔍 Diagnostics</span>
          {#if pipelineDiagnostics?.winning_stage || pipelineDiagnostics?.winningStage}
            <span
              class="px-1.5 py-0.5 text-[10px] bg-cyan-950 text-cyan-400 border border-cyan-800 rounded font-mono"
            >
              {pipelineDiagnostics.winning_stage || pipelineDiagnostics.winningStage}
            </span>
          {/if}
        </button>

        <button
          class="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm active:scale-95 transition-all duration-200"
          on:click={closeModal}
          disabled={savingDraft || approving || rejecting}
        >
          Close
        </button>
      </div>
    </header>

    <!-- 2. Scrollable Side-by-Side Body Container -->
    <div class="flex-1 min-h-0 flex flex-row overflow-hidden relative">
      <!-- Left: Metadata Editor (Independent Scroll) -->
      <main class="flex-1 min-h-0 overflow-y-auto p-6 space-y-6">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section class="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
          <div class="flex items-start gap-4 mb-4">
            {#if coverUrl}
              <div
                class="w-24 h-24 rounded-lg overflow-hidden border border-slate-700 shadow-lg flex-shrink-0"
              >
                <img
                  src={coverUrl}
                  alt="Album Cover"
                  class="w-full h-full object-cover"
                />
              </div>
            {:else}
              <div
                class="w-24 h-24 rounded-lg bg-slate-800 flex items-center justify-center flex-shrink-0 text-slate-500 border border-slate-700"
              >
                <span class="text-2xl">🎵</span>
              </div>
            {/if}
            <div class="flex-1 min-w-0">
              <h4 class="text-sm font-semibold text-slate-100 mb-1">
                Current File Metadata
              </h4>
              <p
                class="text-xs text-slate-400 truncate"
                title={task?.file_path}
              >
                {task?.file_path}
              </p>
            </div>
          </div>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between gap-4">
              <span class="text-slate-400">Title</span>
              <span class="text-slate-200 text-right"
                >{displayValue(currentMetadata.title)}</span
              >
            </div>
            <div class="flex justify-between gap-4">
              <span class="text-slate-400">Edition / Version</span>
              <span class="text-slate-200 text-right"
                >{displayValue(
                  currentMetadata.edition || currentMetadata.version,
                )}</span
              >
            </div>
            <div class="flex justify-between gap-4">
              <span class="text-slate-400">Artist</span>
              <span class="text-slate-200 text-right"
                >{displayValue(currentMetadata.artist)}</span
              >
            </div>
            <div class="flex justify-between gap-4">
              <span class="text-slate-400">Album</span>
              <span class="text-slate-200 text-right"
                >{displayValue(currentMetadata.album)}</span
              >
            </div>
            <div class="flex justify-between gap-4">
              <span class="text-slate-400">Year</span>
              <span class="text-slate-200 text-right"
                >{displayValue(
                  currentMetadata.year || currentMetadata.date,
                )}</span
              >
            </div>
            <div class="flex justify-between gap-4">
              <span class="text-slate-400">Track #</span>
              <span class="text-slate-200 text-right"
                >{displayValue(currentMetadata.track_number)}</span
              >
            </div>
            <div class="flex justify-between gap-4">
              <span class="text-slate-400">Disc #</span>
              <span class="text-slate-200 text-right"
                >{displayValue(currentMetadata.disc_number)}</span
              >
            </div>
            <div class="flex justify-between gap-4">
              <span class="text-slate-400">ISRC</span>
              <span class="text-slate-200 text-right break-all"
                >{displayValue(currentMetadata.isrc)}</span
              >
            </div>
            <div class="flex justify-between gap-4">
              <span class="text-slate-400">MusicBrainz ID</span>
              <span class="text-slate-200 text-right break-all"
                >{displayValue(
                  currentMetadata.mbid || currentMetadata.musicbrainz_id,
                )}</span
              >
            </div>
            <div class="flex justify-between gap-4">
              <span class="text-slate-400">AcoustID</span>
              <span class="text-slate-200 text-right break-all"
                >{displayValue(
                  currentMetadata.acoustid || currentMetadata.acoustid_id,
                )}</span
              >
            </div>
            <div class="flex justify-between gap-4">
              <span class="text-slate-400">Comments</span>
              <span class="text-slate-200 text-right break-all"
                >{displayValue(currentMetadata.comments)}</span
              >
            </div>
          </div>
        </section>

        <section
          class="rounded-xl border border-cyan-700/40 bg-cyan-950/10 p-4"
        >
          <h4 class="text-sm font-semibold text-cyan-200 mb-3">
            Proposed Metadata (Editable)
          </h4>

          {#if noTagsWarning}
            <div
              class="mb-4 px-3 py-2 rounded border border-amber-500/50 bg-amber-950/30 text-amber-200 text-sm flex items-start gap-2"
            >
              <span class="mt-0.5">⚠️</span>
              <span>No embedded tags found. Manual entry required.</span>
            </div>
          {/if}

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label class="sm:col-span-2">
              <span class="block text-xs text-slate-400 mb-1">Title</span>
              <input
                class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100"
                bind:value={proposedMetadata.title}
                on:keydown={handleInputKeydown}
              />
            </label>

            <div class="sm:col-span-2 space-y-1.5">
              <label for="edition" class="text-xs font-semibold text-slate-300"
                >Edition / Version</label
              >
              <input
                id="edition"
                type="text"
                placeholder="e.g. Radio Edit, Remix, Deluxe Edition"
                bind:value={proposedMetadata.edition}
                on:input={handleAutosave}
                on:keydown={handleInputKeydown}
                class="w-full px-3 py-2 bg-slate-900/80 border border-slate-700/60 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500/60 transition-colors"
              />
              {#if proposedMetadata.edition}
                <p class="text-[11px] text-slate-400">
                  Physical tag preview: <span class="text-cyan-400 font-mono"
                    >{proposedMetadata.title} ({proposedMetadata.edition})</span
                  >
                </p>
              {/if}
            </div>

            <label class="sm:col-span-2">
              <span class="block text-xs text-slate-400 mb-1">Artist</span>
              <input
                class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100"
                bind:value={proposedMetadata.artist}
                on:keydown={handleInputKeydown}
              />
            </label>

            <label class="sm:col-span-2">
              <span class="block text-xs text-slate-400 mb-1">Album</span>
              <input
                class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100"
                bind:value={proposedMetadata.album}
                on:keydown={handleInputKeydown}
              />
            </label>

            <label>
              <span class="block text-xs text-slate-400 mb-1">Year</span>
              <input
                class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100"
                bind:value={proposedMetadata.year}
                on:keydown={handleInputKeydown}
              />
            </label>

            <label>
              <span class="block text-xs text-slate-400 mb-1">Track Number</span
              >
              <input
                class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100"
                bind:value={proposedMetadata.track_number}
                on:keydown={handleInputKeydown}
              />
            </label>

            <label>
              <span class="block text-xs text-slate-400 mb-1">Disc Number</span>
              <input
                class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100"
                bind:value={proposedMetadata.disc_number}
                on:keydown={handleInputKeydown}
              />
            </label>

            <details
              class="sm:col-span-2 rounded-lg border border-slate-700 bg-slate-900/50 p-3"
              bind:open={showAdvanced}
            >
              <summary class="cursor-pointer text-sm font-medium text-slate-200"
                >Advanced Tagging</summary
              >
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
                <label>
                  <span class="block text-xs text-slate-400 mb-1"
                    >MusicBrainz ID (MBID)</span
                  >
                  <input
                    class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100"
                    bind:value={proposedMetadata.mbid}
                    on:keydown={handleInputKeydown}
                  />
                </label>

                <label>
                  <span class="block text-xs text-slate-400 mb-1">AcoustID</span
                  >
                  <input
                    class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100"
                    bind:value={proposedMetadata.acoustid}
                    on:keydown={handleInputKeydown}
                  />
                </label>

                <label>
                  <span class="block text-xs text-slate-400 mb-1"
                    >Fingerprint Duration (s)</span
                  >
                  <input
                    class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-300"
                    value={proposedMetadata.acoustid_fingerprint_duration || ""}
                    readonly
                  />
                </label>

                <label class="sm:col-span-2">
                  <span class="block text-xs text-slate-400 mb-1"
                    >AcoustID Fingerprint (Submission Payload)</span
                  >
                  <textarea
                    class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-300 min-h-[90px]"
                    value={proposedMetadata.acoustid_fingerprint || ""}
                    readonly
                  ></textarea>
                </label>

                <label class="sm:col-span-2">
                  <span class="block text-xs text-slate-400 mb-1">ISRC</span>
                  <input
                    class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100"
                    bind:value={proposedMetadata.isrc}
                    on:keydown={handleInputKeydown}
                  />
                </label>

                <label class="sm:col-span-2">
                  <span class="block text-xs text-slate-400 mb-1">Comments</span
                  >
                  <textarea
                    class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100 min-h-[90px]"
                    bind:value={proposedMetadata.comments}
                  ></textarea>
                </label>
              </div>
            </details>
          </div>
          <p class="mt-3 text-xs text-slate-400">
            {#if autosavePending}
              Autosave pending...
            {:else if savingDraft}
              Saving draft...
            {:else}
              Changes are autosaved 1s after typing stops.
            {/if}
          </p>
        </section>
      </div>
    </main>

    <!-- Right: Slide-out Diagnostic Drawer -->
    {#if showDiagnosticsDrawer}
      <aside
        class="w-96 lg:w-[480px] shrink-0 border-l border-slate-800 bg-slate-950 flex flex-col min-h-0 h-full overflow-hidden z-20 shadow-2xl transition-all duration-200"
      >
        <!-- Drawer Header -->
        <div
          class="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60 shrink-0"
        >
          <div class="flex items-center gap-2">
            <span class="text-sm font-semibold text-slate-200"
              >Stage Diagnostics</span
            >
            {#if pipelineDiagnostics?.winning_stage || pipelineDiagnostics?.winningStage}
              <span
                class="px-2 py-0.5 text-xs font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-800/80 rounded"
              >
                {pipelineDiagnostics.winning_stage ||
                  pipelineDiagnostics.winningStage}
              </span>
            {/if}
          </div>
          <button
            type="button"
            class="w-6 h-6 flex items-center justify-center text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded transition-colors text-xs"
            on:click={() => (showDiagnosticsDrawer = false)}
            title="Close Drawer"
          >
            ✕
          </button>
        </div>

        <!-- Drawer Content (Scrollable) -->
        <div
          class="flex-1 min-h-0 overflow-y-auto p-4 space-y-4 text-xs font-sans"
        >
          {#if pipelineDiagnostics}
            <!-- Waterfall Timeline -->
            {#if Array.isArray(pipelineDiagnostics.diagnostics) && pipelineDiagnostics.diagnostics.length > 0}
              <div class="space-y-2">
                <h4
                  class="text-xs font-semibold text-slate-400 uppercase tracking-wider"
                >
                  Waterfall Timeline
                </h4>
                <div class="space-y-1.5">
                  {#each pipelineDiagnostics.diagnostics as diag}
                    <div
                      class="p-2.5 rounded-lg border border-slate-800 bg-slate-900/50 flex flex-col gap-1"
                    >
                      <div class="flex items-center justify-between">
                        <span class="font-mono font-medium text-slate-200"
                          >{diag.stage || "Stage"}</span
                        >
                        <span
                          class="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase {diag.status ===
                            'success' || diag.status === 'hit'
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50'
                            : diag.status === 'skipped'
                              ? 'bg-slate-800 text-slate-400'
                              : diag.status === 'miss' ||
                                  diag.status === 'untrusted' ||
                                  diag.status === 'dropped'
                                ? 'bg-amber-950 text-amber-400 border border-amber-800/50'
                                : diag.status === 'error'
                                  ? 'bg-rose-950 text-rose-400 border border-rose-800/50'
                                  : 'bg-slate-800 text-slate-300'}"
                        >
                          {diag.status || "info"}
                        </span>
                      </div>
                      {#if diag.reason || diag.message}
                        <p class="text-[11px] text-slate-400">
                          {diag.reason || diag.message}
                        </p>
                      {/if}
                      {#if diag.execution_time_ms !== undefined}
                        <span
                          class="text-[10px] text-slate-500 font-mono self-end"
                          >{diag.execution_time_ms.toFixed(1)} ms</span
                        >
                      {/if}
                    </div>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Candidates Evaluation from Diagnostics -->
            {#each (pipelineDiagnostics.diagnostics || []).filter((d) => d.candidates && d.candidates.length > 0) as diag}
              <div class="space-y-2">
                <div class="flex items-center justify-between">
                  <h4
                    class="text-xs font-semibold text-slate-400 uppercase tracking-wider"
                  >
                    {diag.stage} Candidates ({diag.candidates.length})
                  </h4>
                </div>
                <div class="space-y-2">
                  {#each diag.candidates as cand}
                    <div
                      class="p-2.5 rounded-lg border {cand.status === 'WINNER'
                        ? 'border-cyan-700/60 bg-cyan-950/20'
                        : 'border-slate-800 bg-slate-900/60'} space-y-1.5"
                    >
                      <div class="flex items-start justify-between gap-2">
                        <div class="min-w-0">
                          <p class="font-semibold text-slate-200 truncate">
                            {cand.title || "Unknown Title"}
                          </p>
                          <p class="text-[11px] text-slate-400 truncate">
                            {cand.artist || "Unknown Artist"}
                            {#if cand.album} • {cand.album}{/if}
                          </p>
                        </div>
                        {#if cand.status}
                          <span
                            class="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold {cand.status ===
                            'WINNER'
                              ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                              : 'bg-slate-800 text-slate-400'}"
                          >
                            {cand.status}
                          </span>
                        {/if}
                      </div>

                      <div
                        class="text-[10px] text-slate-400 font-mono space-y-0.5 border-t border-slate-800/60 pt-1"
                      >
                        {#if cand.total_score !== undefined || cand.score !== undefined}
                          <div>
                            Total Score: {(cand.total_score !== undefined
                              ? cand.total_score
                              : cand.score * 100
                            ).toFixed(1)}
                          </div>
                        {/if}
                        {#if cand.acoustid_score !== undefined}
                          <div>
                            Acoustic Sim: {(cand.acoustid_score * 100).toFixed(
                              1
                            )}%
                          </div>
                        {/if}
                        {#if cand.duration_diff !== undefined}
                          <div>
                            Duration Diff: {cand.duration_diff.toFixed(1)}s
                          </div>
                        {/if}
                        {#if cand.mbid}
                          <div class="truncate text-slate-500">
                            MBID: {cand.mbid}
                          </div>
                        {/if}
                        {#if cand.reason || cand.reasons}
                          <div class="text-slate-400 italic font-sans">
                            {cand.reason || cand.reasons}
                          </div>
                        {/if}
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            {/each}

            <!-- Root Candidates (fallback if not in diagnostics) -->
            {#if Array.isArray(pipelineDiagnostics.candidates) && pipelineDiagnostics.candidates.length > 0 && !(pipelineDiagnostics.diagnostics || []).some((d) => d.candidates && d.candidates.length > 0)}
              <div class="space-y-2">
                <h4
                  class="text-xs font-semibold text-slate-400 uppercase tracking-wider"
                >
                  Candidate Scores ({pipelineDiagnostics.candidates.length})
                </h4>
                <div class="space-y-2">
                  {#each pipelineDiagnostics.candidates as cand}
                    <div
                      class="p-2.5 rounded-lg border {cand.status === 'WINNER'
                        ? 'border-cyan-700/60 bg-cyan-950/20'
                        : 'border-slate-800 bg-slate-900/60'} space-y-1.5"
                    >
                      <div class="flex items-start justify-between gap-2">
                        <div class="min-w-0">
                          <p class="font-semibold text-slate-200 truncate">
                            {cand.title || "Unknown Title"}
                          </p>
                          <p class="text-[11px] text-slate-400 truncate">
                            {cand.artist || "Unknown Artist"}
                            {#if cand.album} • {cand.album}{/if}
                          </p>
                        </div>
                        {#if cand.status}
                          <span
                            class="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold {cand.status ===
                            'WINNER'
                              ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                              : 'bg-slate-800 text-slate-400'}"
                          >
                            {cand.status}
                          </span>
                        {/if}
                      </div>

                      <div
                        class="text-[10px] text-slate-400 font-mono space-y-0.5 border-t border-slate-800/60 pt-1"
                      >
                        {#if cand.total_score !== undefined || cand.score !== undefined}
                          <div>
                            Total Score: {(cand.total_score !== undefined
                              ? cand.total_score
                              : cand.score * 100
                            ).toFixed(1)}
                          </div>
                        {/if}
                        {#if cand.acoustid_score !== undefined}
                          <div>
                            Acoustic Sim: {(cand.acoustid_score * 100).toFixed(
                              1
                            )}%
                          </div>
                        {/if}
                        {#if cand.duration_diff !== undefined}
                          <div>
                            Duration Diff: {cand.duration_diff.toFixed(1)}s
                          </div>
                        {/if}
                        {#if cand.mbid}
                          <div class="truncate text-slate-500">
                            MBID: {cand.mbid}
                          </div>
                        {/if}
                        {#if cand.reason || cand.reasons}
                          <div class="text-slate-400 italic font-sans">
                            {cand.reason || cand.reasons}
                          </div>
                        {/if}
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Resolved Metadata Preview -->
            {#if pipelineDiagnostics.resolved_metadata || pipelineDiagnostics.resolvedMetadata}
              {@const meta =
                pipelineDiagnostics.resolved_metadata ||
                pipelineDiagnostics.resolvedMetadata}
              {#if meta && Object.keys(meta).length > 0}
                <div class="space-y-1.5 border-t border-slate-800/80 pt-3">
                  <h4
                    class="text-xs font-semibold text-slate-400 uppercase tracking-wider"
                  >
                    Resolved Data
                  </h4>
                  <div
                    class="bg-slate-900/80 rounded-lg p-2.5 border border-slate-800 font-mono text-[11px] space-y-1 text-slate-300"
                  >
                    {#if meta.title}<div>
                        <span class="text-slate-500">Title:</span> {meta.title}
                      </div>{/if}
                    {#if meta.artist}<div>
                        <span class="text-slate-500">Artist:</span> {meta.artist}
                      </div>{/if}
                    {#if meta.album}<div>
                        <span class="text-slate-500">Album:</span> {meta.album}
                      </div>{/if}
                    {#if meta.edition}<div>
                        <span class="text-slate-500">Edition:</span> {meta.edition}
                      </div>{/if}
                    {#if meta.year}<div>
                        <span class="text-slate-500">Year:</span> {meta.year}
                      </div>{/if}
                    {#if meta.musicbrainz_track_id || meta.musicbrainz_id || meta.mbid}
                      <div>
                        <span class="text-slate-500">MBID:</span> {meta.musicbrainz_track_id ||
                          meta.musicbrainz_id ||
                          meta.mbid}
                      </div>
                    {/if}
                    {#if meta.isrc}<div>
                        <span class="text-slate-500">ISRC:</span> {meta.isrc}
                      </div>{/if}
                    {#if meta.acoustid_fingerprint || meta.acoustid}
                      <div>
                        <span class="text-slate-500">AcoustID:</span> {meta.acoustid_fingerprint ||
                          meta.acoustid}
                      </div>
                    {/if}
                  </div>
                </div>
              {/if}
            {/if}
          {:else}
            <div class="text-center py-12 text-slate-500">
              <p class="text-sm">No diagnostic trace available.</p>
              <p class="text-[11px] mt-1 text-slate-600">
                Run a lookup or pipeline simulation to inspect stage execution.
              </p>
            </div>
          {/if}
        </div>
      </aside>
    {/if}
  </div>

    <!-- Track Preview -->
    {#if streamUrl}
      <div
        class="px-5 py-2.5 border-t border-slate-800 bg-slate-950/80 shrink-0"
      >
        <p
          class="text-xs uppercase tracking-wide text-slate-400 mb-1.5 font-medium"
        >
          Track Preview
        </p>
        <audio controls src={streamUrl} class="w-full h-8">
          Your browser does not support audio playback.
        </audio>
      </div>
    {/if}

    {#if lookupStatus}
      <div
        class="absolute bottom-20 left-6 right-6 z-50 pointer-events-auto"
        style="position: absolute; bottom: 5rem; left: 1.5rem; right: 1.5rem; z-index: 50;"
      >
        <div
          class="alert alert-{lookupStatus.type} text-xs py-2 px-4 shadow-2xl flex items-center justify-between transition-all rounded-xl border backdrop-blur-md {lookupStatus.type ===
          'success'
            ? 'bg-emerald-950/90 border-emerald-500/50 text-emerald-200'
            : lookupStatus.type === 'warning'
              ? 'bg-amber-950/90 border-amber-500/50 text-amber-200'
              : lookupStatus.type === 'error'
                ? 'bg-rose-950/90 border-rose-500/50 text-rose-200'
                : 'bg-cyan-950/90 border-cyan-500/50 text-cyan-200'}"
        >
          <div class="flex items-center gap-2.5">
            <span class="text-sm"
              >{lookupStatus.type === "success"
                ? "✓"
                : lookupStatus.type === "warning"
                  ? "⚠️"
                  : lookupStatus.type === "error"
                    ? "✕"
                    : "ℹ"}</span
            >
            <span class="font-medium">{lookupStatus.message}</span>
          </div>
          <button
            class="btn btn-ghost btn-xs btn-circle text-slate-400 hover:text-slate-100 hover:bg-slate-800"
            on:click={() => (lookupStatus = null)}>✕</button
          >
        </div>
      </div>
    {/if}

    <!-- 3. Footer Toolbar (Pinned & Always Visible) -->
    <footer
      class="flex shrink-0 flex-wrap items-center justify-between gap-3 p-4 bg-slate-950 border-t border-slate-800"
    >
      <!-- Left: Destructive Actions -->
      <div class="flex items-center gap-2">
        <button
          class="px-4 py-2 rounded-lg bg-rose-700/80 hover:bg-rose-600 text-white disabled:opacity-60 inline-flex items-center justify-center gap-2 active:scale-95 transition-all duration-200 text-sm font-medium"
          on:click={rejectAndDelete}
          disabled={rejecting || approving || savingDraft}
          title="Reject track candidate and delete physical file from disk"
        >
          {#if rejecting}
            <span
              class="loading loading-spinner loading-xs animate-spin inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full"
            ></span> Deleting...
          {:else}
            🗑️ Reject & Delete
          {/if}
        </button>
      </div>

      <!-- Right: Search Engines & Import -->
      <div class="flex flex-wrap items-center justify-end gap-2 sm:gap-3">
        <button
          class="px-4 py-2 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 disabled:opacity-60 active:scale-95 transition-all duration-200 text-sm"
          on:click={closeModal}
          disabled={savingDraft || approving || rejecting}
        >
          Cancel
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-amber-600 text-white hover:bg-amber-500 disabled:opacity-60 active:scale-95 transition-all duration-200 text-sm"
          on:click={() => saveDraft({ silent: false })}
          disabled={savingDraft || approving || rejecting}
        >
          {savingDraft ? "Saving..." : "Save Draft"}
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-slate-700 text-slate-100 hover:bg-slate-600 disabled:opacity-60 active:scale-95 transition-all duration-200 text-sm"
          on:click={undoLastChange}
          disabled={savingDraft ||
            approving ||
            rejecting ||
            metadataHistory.length < 2}
          title="Undo last metadata edit"
        >
          Undo
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-indigo-700 text-white hover:bg-indigo-600 disabled:opacity-60 inline-flex items-center justify-center gap-2 active:scale-95 transition-all duration-200 text-sm"
          on:click={runMusicBrainzLookup}
          disabled={isScanningAcoustID ||
            isLookingUpMB ||
            isLookingUpISRC ||
            approving ||
            savingDraft ||
            rejecting}
        >
          {#if isLookingUpMB}
            <span
              class="loading loading-spinner loading-xs animate-spin inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full"
            ></span> Looking up...
          {:else}
            🔍 MusicBrainz Lookup
          {/if}
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-emerald-700 text-white hover:bg-emerald-600 disabled:opacity-60 inline-flex items-center justify-center gap-2 active:scale-95 transition-all duration-200 text-sm"
          on:click={runAcoustIDLookup}
          disabled={isScanningAcoustID ||
            isLookingUpMB ||
            isLookingUpISRC ||
            approving ||
            savingDraft ||
            rejecting}
        >
          {#if isScanningAcoustID}
            <span
              class="loading loading-spinner loading-xs animate-spin inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full"
            ></span> Scanning...
          {:else}
            🧬 AcoustID Scan
          {/if}
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-orange-700 text-white hover:bg-orange-600 disabled:opacity-60 inline-flex items-center justify-center gap-2 active:scale-95 transition-all duration-200 text-sm"
          on:click={runISRCLookup}
          disabled={isScanningAcoustID ||
            isLookingUpMB ||
            isLookingUpISRC ||
            isSimulatingPipeline ||
            approving ||
            savingDraft ||
            rejecting}
        >
          {#if isLookingUpISRC}
            <span
              class="loading loading-spinner loading-xs animate-spin inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full"
            ></span> Looking up...
          {:else}
            🎵 ISRC Lookup
          {/if}
        </button>

        <button
          type="button"
          class="px-4 py-2 rounded-lg bg-indigo-600/90 hover:bg-indigo-500 text-white disabled:opacity-60 inline-flex items-center justify-center gap-2 active:scale-95 transition-all duration-200 text-sm font-medium shadow-sm border border-indigo-400/30"
          on:click={runFullPipelineSimulation}
          disabled={isScanningAcoustID ||
            isLookingUpMB ||
            isLookingUpISRC ||
            isSimulatingPipeline ||
            approving ||
            savingDraft ||
            rejecting}
          title="Run full 6-stage metadata waterfall simulation to inspect stage trace diagnostics"
        >
          {#if isSimulatingPipeline}
            <span
              class="loading loading-spinner loading-xs animate-spin inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full"
            ></span> Simulating Pipeline...
          {:else}
            ⚡ Run Full Pipeline
          {/if}
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-cyan-600 text-white hover:bg-cyan-500 disabled:opacity-60 inline-flex items-center justify-center gap-2 active:scale-95 transition-all duration-200 text-sm font-medium"
          on:click={approveAndImport}
          disabled={approving || savingDraft || rejecting}
        >
          {#if approving}
            <svg
              class="animate-spin h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              ></path>
            </svg>
            Approving...
          {:else}
            Approve & Import
          {/if}
        </button>
      </div>
    </footer>
  </div>
</div>

{#if showIsrcPrompt}
  <div
    class="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
  >
    <div
      class="w-full max-w-sm bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-6 text-slate-100"
    >
      <h3 class="text-lg font-bold mb-2">Enter ISRC Code</h3>
      <p class="text-xs text-slate-400 mb-4">
        e.g. USRC12345678 or US-RC1-23-45678
      </p>
      <input
        type="text"
        class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500 transition-colors mb-5"
        bind:value={isrcInputValue}
        on:keydown={(e) => e.key === "Enter" && submitIsrcPrompt()}
        placeholder="ISRC Code"
        autofocus
      />
      <div class="flex justify-end gap-3">
        <button
          class="px-4 py-2 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 active:scale-95 transition-all"
          on:click={closeIsrcPrompt}
        >
          Cancel
        </button>
        <button
          class="px-4 py-2 rounded-lg bg-cyan-600 text-white hover:bg-cyan-500 active:scale-95 transition-all"
          on:click={submitIsrcPrompt}
        >
          Search
        </button>
      </div>
    </div>
  </div>
{/if}
