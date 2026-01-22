from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0005_course_is_full_notified"),
    ]

    operations = [
        migrations.RunSQL(
            # Forward: remove the orphaned column
            sql="""
                ALTER TABLE courses
                DROP COLUMN IF EXISTS current_enrollment_count;
            """,
            # Reverse: restore column with safe default
            reverse_sql="""
                ALTER TABLE courses
                ADD COLUMN current_enrollment_count INTEGER NOT NULL DEFAULT 0;
            """,
        ),
    ]
