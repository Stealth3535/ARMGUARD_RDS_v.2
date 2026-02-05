"""
Management command to regenerate all QR codes with new format
"""
from django.core.management.base import BaseCommand
from qr_manager.models import QRCodeImage


class Command(BaseCommand):
    help = 'Regenerate all QR codes with updated format (cleaner, standard layout)'

    def handle(self, *args, **options):
        qr_codes = QRCodeImage.objects.all()
        total = qr_codes.count()
        
        self.stdout.write(f"Found {total} QR codes to regenerate...")
        
        success_count = 0
        error_count = 0
        
        for qr_code in qr_codes:
            try:
                # Delete old image
                if qr_code.qr_image:
                    qr_code.qr_image.delete(save=False)
                
                # Generate new QR code with updated settings
                qr_code.generate_qr_code()
                qr_code.save()
                
                success_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Regenerated {qr_code.qr_type} QR: {qr_code.reference_id}"
                ))
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(
                    f"✗ Failed to regenerate {qr_code.qr_type} QR {qr_code.reference_id}: {str(e)}"
                ))
        
        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Regeneration complete: {success_count} succeeded, {error_count} failed"
        ))
