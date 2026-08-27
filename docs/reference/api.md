# API reference

_Documentation for this page is in progress._

Snapshot is driven through four Kubernetes API objects. For usage-level
descriptions, see [How to use it](../../README.md#how-to-use-it) and the
[usage guides](../guides/README.md).

<!-- TODO(eng): document each resource field by field, plus the checkpoint/restore lifecycle:
     - PodSnapshot (spec.source.podRef.{name,containers}; status conditions; PodSnapshotContent binding)
     - PodSnapshotContent (cluster-scoped; artifact record; bound to a PodSnapshot)
     - SnapshotJob (spec.podTemplate; spec.podSnapshotTemplate.targetContainers; status conditions; status.podSnapshotName)
     - nvidia.com/restore-from annotation and the snapshot/Restored pod condition
     Generate from the CRD types where possible. -->
