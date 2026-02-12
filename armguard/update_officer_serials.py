"""
Update officer serial numbers to include O- prefix in database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from personnel.models import Personnel

def update_officer_serials():
    """Add O- prefix to officer serial numbers in database"""
    print("\n" + "="*60)
    print("UPDATING OFFICER SERIAL NUMBERS")
    print("="*60)
    
    # Get all officers
    officer_ranks = [r[0] for r in Personnel.RANKS_OFFICER]
    officers = Personnel.objects.filter(rank__in=officer_ranks)
    
    print(f"\nFound {officers.count()} officer(s)")
    print("-" * 60)
    
    updated = 0
    skipped = 0
    
    for officer in officers:
        old_serial = officer.serial
        print(f"\n{officer.get_full_name()} ({officer.rank})")
        print(f"  Current Serial: {old_serial}")
        
        if old_serial.startswith('O-'):
            print(f"  ✓ Already has O- prefix - SKIPPED")
            skipped += 1
        else:
            # The save() method will automatically add O- prefix for officers
            officer.save()
            print(f"  ✓ Updated to: {officer.serial}")
            updated += 1
    
    print("\n" + "="*60)
    print(f"Summary: {updated} updated, {skipped} skipped")
    print("="*60)
    
    # Verify all personnel
    print("\n" + "="*60)
    print("ALL PERSONNEL SERIAL NUMBERS")
    print("="*60)
    
    all_personnel = Personnel.objects.all().order_by('rank')
    for p in all_personnel:
        print(f"{p.get_full_name():30} | Rank: {str(p.rank):10} | Serial (DB): {p.serial:15} | Display: {p.get_serial_display()}")

if __name__ == '__main__':
    update_officer_serials()
