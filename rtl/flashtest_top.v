module flashtest_top(
    input clk,
    input spiflash4x_cs_n,
    inout [3:0] spiflash4x_dq);
    
    wbqspiflash flash_controller(
        .i_clk(clk),
        // Internal wishbone connections
		i_wb_cyc, i_wb_data_stb, i_wb_ctrl_stb, i_wb_we,
		i_wb_addr, i_wb_data,
		// Wishbone return values
		o_wb_ack, o_wb_stall, o_wb_data,
		// Quad Spi connections to the external device
		o_qspi_sck, o_qspi_cs_n, o_qspi_mod, o_qspi_dat, i_qspi_dat,
		o_interrupt);
    );
    
    
endmodule