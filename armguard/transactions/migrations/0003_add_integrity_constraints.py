# Generated migration for transaction integrity constraints

from django.db import migrations, models, connection
from django.db.models import Q

def apply_database_constraints(apps, schema_editor):
    """
    Apply database-specific constraints and indexes
    """
    db_vendor = connection.vendor
    
    if db_vendor == 'postgresql':
        # PostgreSQL-specific indexes and constraints
        with connection.cursor() as cursor:
            # Create unique partial index for personnel (PostgreSQL)
            cursor.execute("""
                CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS personnel_single_active_item_idx 
                ON transactions (personnel_id) 
                WHERE action = 'Take' 
                AND NOT EXISTS (
                    SELECT 1 FROM transactions t2 
                    WHERE t2.item_id = transactions.item_id 
                    AND t2.personnel_id = transactions.personnel_id
                    AND t2.action = 'Return' 
                    AND t2.date_time > transactions.date_time
                );
            """)
            
            # Performance indexes with INCLUDE (PostgreSQL only)
            cursor.execute("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transaction_personnel_history_pg 
                ON transactions (personnel_id, date_time DESC) 
                INCLUDE (action, item_id);
            """)
            
            # Create business rule validation function and trigger
            cursor.execute("""
                CREATE OR REPLACE FUNCTION validate_transaction_business_rules() 
                RETURNS TRIGGER AS $$
                BEGIN
                    IF NEW.action = 'Take' THEN
                        -- Check if personnel already has an active item
                        IF EXISTS (
                            SELECT 1 FROM transactions t1
                            WHERE t1.personnel_id = NEW.personnel_id 
                            AND t1.action = 'Take'
                            AND NOT EXISTS (
                                SELECT 1 FROM transactions t2 
                                WHERE t2.item_id = t1.item_id 
                                AND t2.personnel_id = t1.personnel_id
                                AND t2.action = 'Return' 
                                AND t2.date_time > t1.date_time
                            )
                        ) THEN
                            RAISE EXCEPTION 'Personnel already has an active item - cannot take another';
                        END IF;
                        
                        -- Check if item is already issued
                        IF EXISTS (
                            SELECT 1 FROM transactions t1
                            WHERE t1.item_id = NEW.item_id 
                            AND t1.action = 'Take'
                            AND NOT EXISTS (
                                SELECT 1 FROM transactions t2 
                                WHERE t2.item_id = t1.item_id 
                                AND t2.action = 'Return' 
                                AND t2.date_time > t1.date_time
                            )
                        ) THEN
                            RAISE EXCEPTION 'Item is already issued - cannot be taken';
                        END IF;
                    END IF;
                    
                    IF NEW.action = 'Return' THEN
                        -- Check if item is currently issued to this personnel
                        IF NOT EXISTS (
                            SELECT 1 FROM transactions t1
                            WHERE t1.item_id = NEW.item_id 
                            AND t1.personnel_id = NEW.personnel_id
                            AND t1.action = 'Take'
                            AND NOT EXISTS (
                                SELECT 1 FROM transactions t2 
                                WHERE t2.item_id = t1.item_id 
                                AND t2.personnel_id = t1.personnel_id
                                AND t2.action = 'Return' 
                                AND t2.date_time > t1.date_time
                            )
                        ) THEN
                            RAISE EXCEPTION 'Cannot return item - not currently issued to this personnel';
                        END IF;
                    END IF;
                    
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            cursor.execute("""
                DROP TRIGGER IF EXISTS enforce_transaction_business_rules ON transactions;
                CREATE TRIGGER enforce_transaction_business_rules
                    BEFORE INSERT ON transactions
                    FOR EACH ROW
                    EXECUTE FUNCTION validate_transaction_business_rules();
            """)
    
    elif db_vendor == 'sqlite':
        # SQLite-specific constraints (simpler due to limitations)
        with connection.cursor() as cursor:
            # Basic indexes for SQLite (no CONCURRENTLY, no INCLUDE)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transaction_personnel_history_sqlite 
                ON transactions (personnel_id, date_time DESC);
            """)
            
            # Note: SQLite has limited support for partial indexes and triggers
            # The main business logic validation will be handled at the application level
            print("SQLite detected: Using application-level business rule validation")

def reverse_database_constraints(apps, schema_editor):
    """
    Remove database-specific constraints and indexes
    """
    db_vendor = connection.vendor
    
    with connection.cursor() as cursor:
        if db_vendor == 'postgresql':
            cursor.execute("DROP TRIGGER IF EXISTS enforce_transaction_business_rules ON transactions;")
            cursor.execute("DROP FUNCTION IF EXISTS validate_transaction_business_rules() CASCADE;")
            cursor.execute("DROP INDEX CONCURRENTLY IF EXISTS personnel_single_active_item_idx;")
            cursor.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_transaction_personnel_history_pg;")
        elif db_vendor == 'sqlite':
            cursor.execute("DROP INDEX IF EXISTS idx_transaction_personnel_history_sqlite;")

class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0002_transaction_issued_by'),
    ]

    operations = [
        # Add database constraints for transaction integrity (works on all databases)
        migrations.AddConstraint(
            model_name='transaction',
            constraint=models.CheckConstraint(
                check=Q(action__in=['Take', 'Return']),
                name='valid_transaction_action'
            ),
        ),
        
        # Add constraint to ensure positive values for mags and rounds
        migrations.AddConstraint(
            model_name='transaction',
            constraint=models.CheckConstraint(
                check=Q(mags__gte=0),
                name='positive_mags_count'
            ),
        ),
        
        migrations.AddConstraint(
            model_name='transaction',
            constraint=models.CheckConstraint(
                check=Q(rounds__gte=0),
                name='positive_rounds_count'
            ),
        ),
        
        # Add basic performance index (works on all databases)
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_transaction_item_status_lookup 
            ON transactions (item_id, action, date_time DESC);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS idx_transaction_item_status_lookup;
            """,
        ),
        
        # Apply database-specific constraints and indexes
        migrations.RunPython(
            code=apply_database_constraints,
            reverse_code=reverse_database_constraints,
        ),
    ]