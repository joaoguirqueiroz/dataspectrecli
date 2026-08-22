from __future__ import annotations

from services.cleanup_service import CleanupService


def test_cleanup_service_preview_preserves_cache_files(runtime_root):
    cache_file = runtime_root / "cache" / "preview.tmp"
    cache_file.write_text("temporary", encoding="utf-8")

    result = CleanupService(runtime_root, runtime_root / "cache").preview()

    assert result.dry_run is True
    assert result.scanned_paths == 1
    assert result.removed_files == 0
    assert cache_file.exists()


def test_cleanup_service_removes_only_cache_files(runtime_root):
    cache_file = runtime_root / "cache" / "remove.tmp"
    nested_cache_file = runtime_root / "cache" / "nested" / "remove.cache"
    report_file = runtime_root / "reports" / "keep.json"
    log_file = runtime_root / "logs" / "keep.log"
    data_file = runtime_root / "data" / "keep.json"
    nested_cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("temporary", encoding="utf-8")
    nested_cache_file.write_text("temporary", encoding="utf-8")
    report_file.write_text("important", encoding="utf-8")
    log_file.write_text("important", encoding="utf-8")
    data_file.write_text("important", encoding="utf-8")

    result = CleanupService(runtime_root, runtime_root / "cache").clean(dry_run=False)

    assert result.removed_files == 2
    assert not cache_file.exists()
    assert not nested_cache_file.exists()
    assert report_file.exists()
    assert log_file.exists()
    assert data_file.exists()
