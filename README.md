# Digital Test Script for GLADE .CDL Files

This script is intended to take a `.CDL` file from [GLADE](https://peardrop.co.uk/) and run digital logic tests on it using LTspice.

---

## How to Use

The script references a `data.csv` file for its settings and configurations. You can change the filename in the script if you want to use multiple configurations.

---

## Example Setup

### `data.csv`

| Key         | Value                                 |
|-------------|---------------------------------------|
| CDL         | `C:\\...\\xor.cdl`                    |
| Inputs      | `A,B`                                 |
| Outputs     | `Y` *(must match the .CDL file names)*|
| High        | `5`                                   |
| SpicePath   | `C:\\...\\LTspice\\LTspice.exe`       |
| modelsPath  | `C:\\...\\C5N_models_Glade.txt`       |

> Make sure the `Inputs` and `Outputs` match exactly with the pin names in your `.CDL` file.

---

## Defining Your Tests

Create a `TT.csv` file to define your test vectors. The first row should match the `Inputs` and `Outputs` specified in `data.csv`.

### Example `TT.csv`

```csv
A,B,Y
0,0,0
1,0,1
0,1,1
1,1,0