import csv
import subprocess
import os

CDL = None
High = None
Inputs = []
Outputs = []
InputStates = []
SubCircList = []
SpicePath = None
modelPath = None

def getSettings(csv_file_path):
    global CDL, Inputs, Outputs, High, SpicePath, modelPath
    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        rows = [x for x in csvreader]
    print(rows)
    CDL = rows[1][0]
    Inputs = rows[3]
    Outputs = rows[5]
    High = rows[7][0]
    SpicePath = rows[9][0]
    modelPath = rows[11][0]
    
    
def GetTT(csv_file_path, Inputs, Outputs):
    States = []
    Expected_output = []

    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        header = next(csvreader)

        # More flexible matching
        input_indices = []
        for inp in Inputs:
            if inp in header:
                input_indices.append(header.index(inp))
            else:
                # Attempt matching first character(s) if direct match fails
                matched = False
                for idx, col_name in enumerate(header):
                    if inp[0] == col_name[0]:
                        input_indices.append(idx)
                        matched = True
                        break
                if not matched:
                    raise ValueError(f"Input '{inp}' not found in CSV header.")

        output_indices = []
        for outp in Outputs:
            if outp in header:
                output_indices.append(header.index(outp))
            else:
                raise ValueError(f"Output '{outp}' not found in CSV header.")

        for row in csvreader:
            if row:
                States.append([int(row[i]) for i in input_indices])
                Expected_output.append([int(row[i]) for i in output_indices])

    return States, Expected_output


def getSubCirc(CDLFile):
    CDLf= open(CDLFile, "r")
    fileText = CDLf.read()
    subckt_line = [line for line in fileText.splitlines() if line.startswith('.SUBCKT')][0]

    # Splitting the line into a list
    subckt_list = subckt_line.split()
    return subckt_list

def GenerateTest(State):
    global CDL, High, SubCircList, Inputs,modelPath
    state = [High if x == 1 else x for x in State]
    StateCommands = ""

    for i in range(len(Inputs)):
        StateCommand = f"V{Inputs[i]} {Inputs[i]} 0 DC {state[i]}\n"
        StateCommands = StateCommands +  StateCommand
    #print(StateCommands)
    
    SubCircInstance = f"xSubCirc {' '.join(SubCircList[2:])} {SubCircList[1]}"
    #print(SubCircInstance)

    SimFile =f"""
.include {CDL}
.include {modelPath}
.GLOBAL vdd vss
vdd vdd 0 5V
vss vss 0 0V

{StateCommands}
{SubCircInstance}

.op
.backanno
.end
"""
    return SimFile

def runSimFile(SimFile, SpicePath, SimOut):
    os.makedirs(SimOut, exist_ok=True)

    netlist_path = os.path.join(SimOut, "simulation.cir")
    with open(netlist_path, 'w') as f:
        f.write(SimFile)

    cmd = [
        SpicePath,
        "-b",  
        "-ascii",  
        netlist_path
    ]

    print(f"Running LTspice simulation: {netlist_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("Error running LTspice:")
        print(result.stderr)
        return None
    else:
        print("LTspice simulation completed successfully.")
    
    # Return the path to the simulation output (.raw)
    raw_file_path = os.path.splitext(netlist_path)[0] + ".raw"
    return raw_file_path

def ParseSimOut(SimLog, Inputs, Outputs):
    var_names = []
    values = []
    capture_vars = False
    capture_vals = False
    reading_values = False

    with open(SimLog, 'r') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        line = line.strip()

        if line.startswith("Variables:"):
            capture_vars = True
            continue
        elif line.startswith("Values:"):
            capture_vars = False
            capture_vals = True
            reading_values = True
            continue

        if capture_vars:
            parts = line.split()
            if len(parts) >= 2 and parts[1].startswith("V("):
                var_names.append(parts[1][2:-1].lower())  # e.g., V(a) -> a

        elif capture_vals and reading_values:
            parts = line.split()
            # First line after 'Values:' includes the index number, strip it
            if parts and parts[0].isdigit():
                parts = parts[1:]
            values.extend([float(val) for val in parts])
            if len(values) >= len(var_names):
                break

    return dict(zip(var_names, values))



def FormatTruthTable(states, outputs, Inputs, Outputs, expected_outputs):
    """
    Format the truth table with evenly spaced columns and color output comparison.
    """
    from colorama import Fore, Style, init
    init(autoreset=True)

    columns = Inputs + Outputs
    col_widths = [max(len(col), 5) for col in columns]

    header = " | ".join(col.ljust(width) for col, width in zip(columns, col_widths))
    separator = "-+-".join("-" * width for width in col_widths)
    lines = [header, separator]

    error_detected = False

    for i, (input_state, output_state) in enumerate(zip(states, outputs)):
        expected = expected_outputs[i]
        input_strs = [str(val).ljust(width) for val, width in zip(input_state, col_widths[:len(Inputs)])]
        output_strs = []

        for actual, exp, width in zip(output_state, expected, col_widths[len(Inputs):]):
            val = str(actual if actual is not None else "X").ljust(width)
            if actual == exp:
                val = Fore.GREEN + val + Style.RESET_ALL
            else:
                val = Fore.RED + val + Style.RESET_ALL
                error_detected = True
            output_strs.append(val)

        lines.append(" | ".join(input_strs + output_strs))

    if error_detected:
        lines.append(Fore.RED + "\nError detected, see red values" + Style.RESET_ALL)
    else:
        lines.append(Fore.GREEN + "\nAll Tests Passed!" + Style.RESET_ALL)

    return "\n".join(lines)
def main():
    global SubCircList, Inputs, Outputs, SpicePath, outputs
    getSettings("data.csv")
    states, expected_outputs = GetTT("TT.csv", Inputs, Outputs)
    SubCircList = getSubCirc(CDL)
    output_logical_values = []
    for state in states:
        runSimFile(GenerateTest(state), SpicePath, "SimOut")
        out = ParseSimOut("SimOut\\simulation.raw",Inputs,Outputs)
        logic_out = []
        for out_var in Outputs:
            val = out.get(out_var.lower(), 0)
            if abs(val) < 0.1:
                logic_out.append(0)
            elif abs(val - float(High)) < 0.1:
                logic_out.append(1)
            else:
                logic_out.append(None)  # undefined or floating

        output_logical_values.append(logic_out)
        print(f"Raw: {out} => Logic: {logic_out}")

    print("All simulated output logic values:")
    print(FormatTruthTable(states, output_logical_values, Inputs, Outputs,expected_outputs))

main()


#print("States:", states)
#print("Expected Outputs:", outputs)

SimScript ="""
.GLOBAL vdd vss
vdd vdd 0 5V
vss vss 0 0V
"""