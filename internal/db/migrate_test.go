package db

import (
	"os"
	"path/filepath"
	"testing"
)

func TestVersionLockPath(t *testing.T) {
	path := versionLockPath()
	if path == "" {
		t.Fatal("versionLockPath() returned empty")
	}
	if !filepath.IsAbs(path) {
		t.Errorf("expected absolute path, got %q", path)
	}
}

func TestAlembicConfigPath_Default(t *testing.T) {
	path := alembicConfigPath()
	if path != "alembic.ini" {
		t.Errorf("expected 'alembic.ini', got %q", path)
	}
}

func TestAlembicConfigPath_Override(t *testing.T) {
	t.Setenv("ALEMBIC_CONFIG", "/custom/path/alembic.ini")
	path := alembicConfigPath()
	if path != "/custom/path/alembic.ini" {
		t.Errorf("expected '/custom/path/alembic.ini', got %q", path)
	}
}

func TestDotEnvPath_Default(t *testing.T) {
	path := dotEnvPath()
	if path != ".env" {
		t.Errorf("expected '.env', got %q", path)
	}
}

func TestDotEnvPath_Override(t *testing.T) {
	t.Setenv("DOT_ENV_PATH", "/custom/path/.env")
	path := dotEnvPath()
	if path != "/custom/path/.env" {
		t.Errorf("expected '/custom/path/.env', got %q", path)
	}
}

func TestListMigrationFiles(t *testing.T) {
	dir := t.TempDir()

	// Create some test files
	files := []string{"001_init.py", "002_add_users.py", "README.md", "003_alter.py"}
	for _, f := range files {
		if err := os.WriteFile(filepath.Join(dir, f), []byte(""), 0o644); err != nil {
			t.Fatal(err)
		}
	}

	// Create a subdirectory (should be ignored)
	if err := os.Mkdir(filepath.Join(dir, "subdir"), 0o755); err != nil {
		t.Fatal(err)
	}

	result, err := listMigrationFiles(dir)
	if err != nil {
		t.Fatal(err)
	}

	expected := 3 // only .py files, not README.md or subdir
	if len(result) != expected {
		t.Errorf("expected %d files, got %d: %v", expected, len(result), result)
	}
}

func TestFindNewFile(t *testing.T) {
	before := []string{"a.py", "b.py", "c.py"}
	after := []string{"a.py", "b.py", "c.py", "d.py"}

	got := findNewFile(before, after)
	if got != "d.py" {
		t.Errorf("expected 'd.py', got %q", got)
	}
}

func TestFindNewFile_NoNew(t *testing.T) {
	before := []string{"a.py", "b.py"}
	after := []string{"a.py", "b.py"}

	got := findNewFile(before, after)
	if got != "" {
		t.Errorf("expected empty string, got %q", got)
	}
}

func TestFindNewFile_EmptyBefore(t *testing.T) {
	before := []string{}
	after := []string{"a.py"}

	got := findNewFile(before, after)
	if got != "a.py" {
		t.Errorf("expected 'a.py', got %q", got)
	}
}

func TestIsEmptyMigration_Empty(t *testing.T) {
	content := `"""empty migration"""
def upgrade():
    pass

def downgrade():
    pass
`
	dir := t.TempDir()
	path := filepath.Join(dir, "empty_migration.py")
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}

	empty, err := isEmptyMigration(path)
	if err != nil {
		t.Fatal(err)
	}
	if !empty {
		t.Error("expected empty migration to be detected as empty")
	}
}

func TestIsEmptyMigration_NonEmpty(t *testing.T) {
	content := `"""actual migration"""
def upgrade():
    op.create_table('users', ...)

def downgrade():
    op.drop_table('users')
`
	dir := t.TempDir()
	path := filepath.Join(dir, "actual_migration.py")
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}

	empty, err := isEmptyMigration(path)
	if err != nil {
		t.Fatal(err)
	}
	if empty {
		t.Error("expected non-empty migration to be detected as non-empty")
	}
}

func TestIsEmptyMigration_NoOp(t *testing.T) {
	// Migration with op. but no actual up/down pattern
	content := `"""migration with operation"""
def upgrade():
    op.execute("SELECT 1")
def downgrade():
    pass
`
	dir := t.TempDir()
	path := filepath.Join(dir, "op_migration.py")
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}

	empty, err := isEmptyMigration(path)
	if err != nil {
		t.Fatal(err)
	}
	if empty {
		t.Error("expected migration with op. to be non-empty")
	}
}