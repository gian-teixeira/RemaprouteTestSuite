<h1><span style="font-variant-caps: small-caps;">Remaproute</span> Test Suite</h1>

The program is designed to accept a path that contains route measures, which should be formatted in the style of traceroute. It group up the routes by source and destiny and use the increasing timestamp ordering to simulate changes to these routes. The built changes are then sent to <a href="#" style="font-variant-caps: small-caps;">Remaproute</a>, that emulates the online web environment. 

## Execution

The execution is done through the script `simulator`. Just run
```bash
simulator <command> <args?>
```

<table border="0">
<tr>
    <td><b>Command</b></td>
    <td><b>Function</b></td>
</tr>
<tr>
    <td style="vertical-align:top;">simulate</td>
    <td>
    <p>Uses the provided paths folder to execute the tests with <span style="font-variant-caps: small-caps;">Remaproute</span>. It generates three tables :</p>
    <table border="0" style="margin-left:2rem; margin-top: -1rem;">
        <tr style="background:transparent; border:none;">
            <td style="vertical-align:top; border:none;">
                <span style="
                    display:block; 
                    text-align:left;
                    font-family:monospace;
                ">sample.csv</tt></td>
            <td style="
                vertical-align:top; 
                border:none;
            ">data for each route pair</td>
        </tr>
        <tr style="background:transparent; border:none;">
            <td style="vertical-align:top; border:none;">
                <span style="
                    display:block; 
                    text-align:left;
                    font-family:monospace;
                ">zone.csv</span></td>
            <td style="
                vertical-align:top;
                border:none;
            ">data for each local change zone</td>
        </tr>
        <tr style="background:transparent; border:none;">
            <td style="vertical-align:top; border:none;">
                <span style="
                    display:block; 
                    text-align:left;
                    font-family:monospace;
                ">detection.csv</span></td>
            <td style="
                vertical-align:top; 
                border:none;
            ">data for each hop send to remap</td>
        </tr>
    </table>
    Arguments:
    <table border="0" style="margin-left:2rem;">
        <tr style="background:transparent; border:none;">
            <td style="vertical-align:top; border:none;">
                <span style="
                    display:block; 
                    text-align:left;
                    font-family:monospace;
                "> -i</tt></td>
            <td style="
                vertical-align:top; 
                border:none;
            ">net interface to be used by remaprt</td>
        </tr>
        <tr style="background:transparent; border:none;">
            <td style="vertical-align:top; border:none;">
                <span style="
                    display:block; 
                    text-align:left;
                    font-family:monospace;
                "> -p</span></td>
            <td style="
                vertical-align:top;
                border:none;
            ">folder containing paths</td>
        </tr>
        <tr style="background:transparent; border:none;">
            <td style="vertical-align:top; border:none;">
                <span style="
                    display:block; 
                    text-align:left;
                    font-family:monospace;
                "> -l</span></td>
            <td style="
                vertical-align:top; 
                border:none;
            ">log file</td>
        </tr>
    </table>
    </td>
</tr>
<tr>
    <td style="vertical-align:top;">stats</td>
    <td>Uses the data gathered by <i>simulate</i> to plot the graphs and display a summary with some metrics.</td>
</tr>
<tr>
    <td style="vertical-align:top;">help</td>
    <td>Shows help information.</td>
</tr>
</table>

> The program needs root access.

## License

This project is licensed under the terms of the MIT license.