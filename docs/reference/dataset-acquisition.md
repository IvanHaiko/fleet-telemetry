# UAV-SEAD and NIST/VTO research acquisition

## Current retention after authorized DJI removal, 2026-11-06

The maintainer explicitly requested removal of DJI data to recover disk space.
The 24 standalone DJI/Mavic device-set directories, decoded DJI research copies,
first-file exports and portable decoder were removed. This deleted 223 files
totalling 31,073,204,141 bytes (about 31.1 GB), including 30,821,848,351 source
bytes. No other source collection or runtime storage was selected for deletion.

Current retained source data is **42,172,781,907 bytes** (about 42.2 GB):
29,890,861,009 bytes of UAV-SEAD and 12,281,920,898 bytes of other NIST/VTO
sources. The latter comprises 119 files, including 33 archives. All 4,359
protected source files retain their pre-removal paths, sizes and last-write
timestamps. No full content rehash was needed for the scoped deletion check.

Historical source inventories, acquisition receipts, checksums and field/schema
reports remain. Acquisition numbers below describe the original completed
download, not current payload availability. Mixed non-DJI archives were not
rewritten to remove embedded application history. This is space reclamation,
not a claim that every DJI-related byte was purged from every backup.

Private evidence is `dji-removal-manifest.json` and
`dji-removal-verification.json` in the acquisition directory. The pre-removal
audit is preserved as `acquisition-audit-before-dji-removal.json`; the current
audit recognizes deliberate removal separately from source access refusals.
The original NIST bulk downloaders refuse to restore the removed selection;
restoring it requires a newly authorized acquisition plan. Reacquisition, not
a local rollback, would be required to recover removed payloads.

## Authorized scope, 2026-11-06

Acquire UAV-SEAD and a NIST/VTO flight-data research subset locally. The
maintainer first requested both sources, then limited NIST/VTO to approximately
50 GB after the full forensic collection exceeded available disk space.
UAV-SEAD is separate from that limit. No source adapter, service, model,
canonical admission, Git commit or publication is authorized by this acquisition.

**Historical acquisition outcome, before removal:** UAV-SEAD completed and reconciled. The available NIST/VTO
subset completed with explicitly unavailable source files and one source-notice
checksum disagreement. Total acquired source-file bytes were 72,994,630,258
(about 73.0 GB). No incomplete data-file or range payload remains.

Retained originals, source inventories, transfer scripts, receipts and reports are in
ignored `.local-discovery/dataset-acquisition-20261106-001/`. Raw locations,
identifiers, mobile backups and derived measurements must remain local.

## UAV-SEAD

The later [structural inspection and field catalog](dataset-structure.md)
separately records observed schema coverage, decoded DJI research files and
limitations for link-loss analysis. Acquisition checks below remain distinct
from that inspection and do not establish semantic source admission.

- Source: [UAV-SEAD dataset](https://huggingface.co/datasets/aykutkabaoglu/uav-flight-anomaly-dataset).
- Snapshot: `774a336a1d1d06b248927a35c2ea1f6869e9e1a4`.
- Publisher: Aykut Kabaoglu; dataset card declares CC BY 4.0.
- Listed snapshot: 4,240 files, 29,890,861,009 bytes, including 3,968 `.ulg`
  paths, annotations and supporting material.
- Four `.ulg` paths are empty in the remote snapshot. Preserve those bytes as
  source evidence; they are not valid flight logs.
- Final acquisition reconciles all 4,240 files and 29,890,861,009 bytes. There
  are 3,951 distinct `.ulg` content hashes; identical files and empty files must
  not be counted as independent flights. Six `.ulg` files fail the ULog magic
  check, including the four empty files. All acquired bytes still match the
  pinned publisher hashes; no original is repaired or discarded.
- The dataset card describes 1,396 categorized flights. File count is not
  independent-flight count; the downloaded scope and reviewed annotation scope
  must be reconciled before constructing training examples.

The transfer pins each URL to the snapshot, verifies remote length and LFS
SHA-256 (or Git blob identity for non-LFS files), then publishes the local file.
Partial files remain separate. Local SHA-256 receipts record each retained file.
An empty source file can match its publisher checksum while failing ULog magic.
Framing, firmware definitions, physical provenance and clock semantics are not
validated by acquisition.

## NIST/VTO selection

The [NIST CFReDS index](https://cfreds-archive.nist.gov/drone-images.html) links
public Google Drive forensic material produced by the VTO Drone Forensics
Program. Its controlled-device acquisitions include aircraft, controllers and
mobile devices; a device set is not a flight or a confirmed failure episode.

The inventory walked all 79 linked roots. It recorded 773 file entries; some
roots overlap. After deduplicating Google Drive file IDs, declared size is about
2.87 TB. This complete forensic corpus is outside the revised download scope.

The local selection plans 49,403,257,574 bytes: 75 ZIP archives from 47 device
sets, together with selected README and checksum files. It prioritizes explicit
flight-log and DJI Assistant exports, then smaller logical acquisitions and
remaining iOS backups. It excludes physical disk/chip images, underwater systems
and rovers. This is a purposeful convenience sample, not a representative fleet
sample. Dataset/model labels are source declarations and need separate review.

Final acquisition retained 235 files and 43,103,769,249 bytes: **71 ZIP archives
from 45 device sets**, plus source notices/checksums. The 43 unavailable files
are four archives and 39 source-notice/checksum files requiring Google sign-in.
Their combined declared size is 6,299,488,325 bytes. They are recorded in
`nist-summary.json`; no sign-in page is accepted as source data. All missing
selected files reconcile to these explicit access refusals, and the available
subset remains below the maintainer's 50 GB limit.

The archives contain 44,420 members and declare 69,184,825,722 uncompressed
bytes. Observed suffix counts include 1,733 `.txt`, 513 `.dat`, 147 `.bin`,
838 `.json` and 122 `.csv` members. These are file counts, not validated logs,
independent flights or link-loss episodes. Mobile backups can also encode
original paths in their backup manifests.

The retrieved DF019 2018 README supplies the dataset's MIT-style copyright and
permission text. Retain applicable notices with each acquired source. Some old
Google Drive links require sign-in despite publicly listed folders; an HTML
sign-in response is refused instead of being saved as a data file. Final
unavailable-file accounting remains required.

Transfers verify declared byte length and compute local SHA-256, MD5 and SHA-1.
The slow Google Drive transfer also uses exact bounded HTTP byte ranges, retains
completed prefixes and hashes temporary ranges. Each response must match the
requested Content-Range, total length and source ETag when one is supplied.
Ranges are assembled in order and the final file is checked again.
ZIP central directories are inspected without extraction. Available publisher
checksum sidecars must be compared separately: a locally computed checksum alone
does not prove agreement with an independently published checksum. Central
directory readability does not establish member CRC validity or log semantics.
Archives remain packed; their extracted size can exceed the download budget.

Final sidecar comparison finds 89 matching publisher checksums and two
disagreements, both for the same DF049 Mavic Air April 2018 README. A separate
HTTP retrieval of that README and its MD5/SHA-1 files reproduced all retained
bytes. The source sidecars disagree with the currently served README; the
originals and the recheck are retained unchanged. This source-notice issue is
not evidence of an archive payload mismatch. No blanket checksum-pass claim
is made for NIST/VTO.

## Evidence and use boundary

The private acquisition directory retains:

- `hf-metadata.json`, `hf-tree.json`: pinned source metadata.
- `nist-roots.json`, `nist-inventory/`, `nist-files.json`: public-folder inventory.
- `nist-selection.json`: the bounded NIST/VTO selection.
- `uav-sead-receipts.jsonl`, `nist-receipts.jsonl`: completed-file receipts.
- `uav-sead-summary.json`, `nist-summary.json`: transfer outcomes when finished.
- `acquisition-audit.json`: final receipt, size and source-checksum reconciliation.
- `nist-notice-recheck.json`: the reproduced source-notice checksum disagreement.

## Verification outcome

The original `audit_acquisition.py` reconciliation reported UAV-SEAD `complete` and
NIST/VTO `acquired_with_source_issues`. All acquired files had completed
receipts and expected byte lengths; UAV-SEAD matches the pinned published
hashes. NIST/VTO source refusals and the README checksum disagreements remain
explicit. ZIP member CRC, whole-ULog framing, firmware semantics and link-loss
labels were not validated. After the authorized removal, the same audit reports
NIST/VTO `retained_subset_verified_after_authorized_removal`; deliberately removed
paths are accounted separately. Documentation whitespace and Git diff checks are
run separately; no services, integration suite or ML training is started.

Downloaded examples are not admitted to existing canonical profiles. Neither
source currently supplies a verified radio-link-loss training dataset for this
project. Evaluate channel definitions, available link fields, event labels,
native time, missingness and source coverage before building features. Group
exact duplicate sources together when designing training/evaluation splits.

No dependencies or runtime services are added. Full-stream transfers check for
40 GiB of free space before each file; ranged acquisition requires 60 GiB before
starting. Resume uses a separate partial file and requires the exact HTTP
range response. Rollback stops the acquisition; it does not delete originals,
clear existing runtime storage or reset any pipeline offsets.
