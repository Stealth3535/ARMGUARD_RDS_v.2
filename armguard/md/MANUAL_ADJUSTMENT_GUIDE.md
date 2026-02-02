# Manual PDF Position Adjustment Guide

## ✅ What I Just Did

Created a **manual adjustment system** where you can easily shift all text positions up or down to fix the cutting issue.

## 📁 Files Created

1. **`print_handler/pdf_filler/form_config.py`** - Configuration file where you adjust positions
2. **`test_adjust_positions.py`** - Tool that generates test PDFs with different offsets
3. **Test PDFs in:** `core/media/transaction_forms/test_adjustments/`

## 🎯 Quick Start - Fix Cutting Issue

### Step 1: Print Test PDFs
I just generated 5 test PDFs with different shifts:
- `test_offset_0pts.pdf` - Original position (current cutting issue)
- `test_offset_18pts.pdf` - Shifted down 0.25 inch
- `test_offset_36pts.pdf` - Shifted down 0.5 inch ⭐ LIKELY BEST
- `test_offset_54pts.pdf` - Shifted down 0.75 inch
- `test_offset_72pts.pdf` - Shifted down 1 inch

**Print all 5 to your EPSON L3210 and compare them**

### Step 2: Find Best Offset
Look at each printed form and check:
- ✅ Is "PHILIPPINE AIR FORCE" header visible at top?
- ✅ Are all text fields properly aligned?
- ✅ Are signatures visible at bottom?
- ✅ Does nothing go off the bottom edge?

**Recommendation:** Usually 36 or 54 points works best (0.5" to 0.75")

### Step 3: Apply Your Chosen Offset

Open: [print_handler/pdf_filler/form_config.py](print_handler/pdf_filler/form_config.py)

Find this line near the top:
```python
VERTICAL_OFFSET = 36  # points (72 points = 1 inch)
```

Change the number to your chosen value:
```python
VERTICAL_OFFSET = 36  # If 36 point offset looked best
# or
VERTICAL_OFFSET = 54  # If 54 point offset looked best
```

Save the file.

### Step 4: Test with Real Transaction

Run:
```bash
python test_print_now.py
```

Print the PDF and verify it looks correct.

## 📊 Understanding the Values

```
Points  | Inches | When to Use
--------|--------|-------------
0       | 0.00"  | Original (currently cutting top)
18      | 0.25"  | Slight adjustment
36      | 0.50"  | Standard printer margin ⭐
54      | 0.75"  | Larger printer margin
72      | 1.00"  | Maximum adjustment
```

## 🔧 Advanced: Individual Field Adjustment

If one specific field needs adjustment (after global offset is set):

Edit [form_config.py](print_handler/pdf_filler/form_config.py):

```python
FIELD_ADJUSTMENTS = {
    # Move date field 5 points to the right
    'date': {'x': 5, 'y': 0},
    
    # Move personnel name down 2 points and left 3 points
    'personnel_name': {'x': -3, 'y': 2},
}
```

Available field names:
- `date`
- `personnel_name`, `personnel_rank`, `personnel_serial`, `personnel_unit`, `personnel_tel`
- `item_type`, `item_serial`, `mags`, `rounds`
- `duty_type`
- `received_by`, `issued_by`

## 🔄 Generate More Test PDFs

To test other offset values:

1. Edit [form_config.py](print_handler/pdf_filler/form_config.py)
2. Change `VERTICAL_OFFSET` to desired value
3. Run: `python test_adjust_positions.py`
4. This generates test PDFs with: 0, 18, 36, 54, 72 points

Or manually test a specific value:
```python
# In form_config.py
VERTICAL_OFFSET = 42  # Test 42 points (custom value)
```

Then:
```bash
python test_print_now.py
```

## ⚙️ Configuration File Structure

**[print_handler/pdf_filler/form_config.py](print_handler/pdf_filler/form_config.py)**:

```python
# MAIN ADJUSTMENT - Change this number
VERTICAL_OFFSET = 36  # Move all text down 0.5 inch

# Optional: Horizontal adjustment
HORIZONTAL_OFFSET = 0  # Move all text left/right

# All field positions are in this dictionary
UPPER_FORM = {
    'date': {'x': 415, 'y': 116, 'size': 9},
    'personnel_name': {'x': 88, 'y': 160, 'size': 9},
    # ... etc
}

# Fine-tune individual fields
FIELD_ADJUSTMENTS = {
    # Add adjustments here if needed
}
```

## 📝 Quick Checklist

### To Fix Top Cutting:

- [ ] Run `python test_adjust_positions.py`
- [ ] Print all 5 test PDFs
- [ ] Compare and pick best one (likely 36 or 54)
- [ ] Open `form_config.py`
- [ ] Change `VERTICAL_OFFSET = 36` (to your chosen value)
- [ ] Save file
- [ ] Run `python test_print_now.py` to verify
- [ ] Print and confirm it's perfect

### Current Settings:
- Default: `VERTICAL_OFFSET = 36` (0.5 inch down)
- This should fix most printer top margin issues

## 🎯 Troubleshooting

### Top Still Cut Off
→ Increase `VERTICAL_OFFSET` (try 54 or 72)

### Bottom Cut Off  
→ Decrease `VERTICAL_OFFSET` (try 18 or 0)
→ Or: Ensure Legal paper (8.5" × 14") is loaded, not Letter (8.5" × 11")

### Text Misaligned Horizontally
→ Adjust `HORIZONTAL_OFFSET` or use `FIELD_ADJUSTMENTS`

### One Field Wrong Position
→ Use `FIELD_ADJUSTMENTS` dictionary for that specific field

### Want to Reset to Original
→ Set `VERTICAL_OFFSET = 0` and `HORIZONTAL_OFFSET = 0`

## 📂 File Locations

- **Config:** `print_handler/pdf_filler/form_config.py`
- **Test Tool:** `test_adjust_positions.py`
- **Test PDFs:** `core/media/transaction_forms/test_adjustments/`
- **Form Filler:** `print_handler/pdf_filler/form_filler.py`

## 💡 Pro Tips

1. **Test first!** Always use `test_adjust_positions.py` to generate comparison PDFs before applying to production

2. **Print comparison:** Print multiple test PDFs at once to easily compare side-by-side

3. **Legal paper required:** Ensure you're using Legal (8.5" × 14"), not Letter (8.5" × 11")

4. **Incremental adjustment:** If 36 is close but not perfect, try 40 or 42 (custom values work too)

5. **Template alignment:** The adjustment shifts YOUR TEXT only, not the printed form template underneath

---
**Status:** Ready for manual adjustment
**Default Setting:** VERTICAL_OFFSET = 36 points (0.5 inch down)
**Test PDFs:** Generated and ready in test_adjustments folder
