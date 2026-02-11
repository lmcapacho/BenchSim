`timescale 1ns / 1ps

module testbench;
    reg a, b;
    wire y;

    // Instanciar el módulo a probar
    and_gate uut (
        .a(a),
        .b(b),
        .y(y)
    );

    initial begin
        // Crear un archivo de salida para GTKWave
        $dumpfile("waveform.vcd");
        $dumpvars(0, testbench);

        // Secuencia de pruebas
        a = 0; b = 0; #10;
        a = 0; b = 1; #10;
        a = 1; b = 0; #10;
        a = 1; b = 1; #10;

        // Finalizar la simulación
        $finish;
    end
endmodule

