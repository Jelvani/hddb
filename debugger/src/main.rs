mod fpga_mem{
	use wishbone_bridge::UsbBridge;
	use wishbone_bridge::Bridge;
	pub struct FpgaMem {
		bridge: Bridge,
		base: u32,
		size: u32, //memory size in bytes
		pub len: u32 //array length (for 4 byte words)
	}
	
	impl FpgaMem {
		
		pub fn new(pid: u16, base: u32, size: u32) -> Self {
			FpgaMem{bridge: UsbBridge::new().pid(pid).create().unwrap(),
					base: base,
					size: size,
					len: size/4}
		}

		#[allow(dead_code)]
		pub fn get(&self, index: u32) -> u32 {
			assert!(index< self.len);
			self.bridge.peek(self.base + index*4).unwrap()
		}

		#[allow(dead_code)]
		pub fn set(&self, index: u32, val: u32){
			//println!("addr: {:#x} set: {}",self.base + index*4,val);
			assert!(index < self.len);
			self.bridge.poke(self.base + index*4,val).unwrap()
		}

	}
}


use std::{
    fs::File,
    io::{prelude::*, BufReader},
    path::Path,
    thread,
};

fn lines_from_file(filename: impl AsRef<Path>) -> Vec<String> {
    let file = File::open(filename).expect("no such file");
    let buf = BufReader::new(file);
    buf.lines()
        .map(|l| l.expect("Could not parse line"))
        .collect()
}



fn do_debug(mem: &fpga_mem::FpgaMem, app: &mut App) {
    
    for (i,sym) in app.symbol_table.iter().enumerate() {

        //select register i
        mem.set(0,i as u32);

        //set virtual_clock register up for 1 tick
        if(i==0){
            mem.set(1,1);
        }

        app.reg_vals[i] = mem.get(1).to_string();

    }
}

fn fetch(mem: &fpga_mem::FpgaMem,  app: &mut App) {
    
    for (i,sym) in app.symbol_table.iter().enumerate() {

        //select register i
        mem.set(0,i as u32);

        app.reg_vals[i] = mem.get(1).to_string();

    }
}

fn push(mem: &fpga_mem::FpgaMem,  app: &mut App, index: usize, val: String) {
    
    mem.set(0,index as u32);
    mem.set(1,val.parse::<u32>().unwrap());

    
}




use std::io::{stdin, stdout, Write};

use std::{
    io::{self, Stdout},
    time::Duration,
};

use anyhow::{Context, Result};
use crossterm::{
    event::{self, Event, KeyCode, KeyEventKind},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{prelude::*, widgets::*};

fn main() -> Result<()> {

    let lines = lines_from_file("/mnt/c/Users/Admin/Desktop/phd_research/hdl_printf/symbol_table.txt");
    
    
    let mut terminal = setup_terminal().context("setup failed")?;
    let mut app = App::new(lines);
    run(&mut terminal, &mut app).context("app loop failed")?;
    restore_terminal(&mut terminal).context("restore terminal failed")?;
    Ok(())
}


struct App {
    mod_register: bool, 
    register_input: String, //input from keyboard to update a register value
    tab_idx: usize, //current selected register index
    tab_offset: Vec<usize>, //offset for register name scrolling
    symbol_table: Vec<String>,  //register names
    reg_vals: Vec<String>, //register values
    cursor_x: u16,
    cursor_y: u16,

}

impl App {
    fn new(symbol_table: Vec<String>) -> App {
        App { mod_register: false,
            register_input: String::new(),
            tab_idx: 0, 
            tab_offset: vec![0; symbol_table.len()],
            symbol_table: symbol_table.clone(),
            reg_vals: vec!["0".to_string(); symbol_table.len()],
            cursor_x: 0,
            cursor_y: 0}
    }

    fn enter_char(&mut self, new_char: char) {
        self.register_input.insert(self.register_input.len(), new_char);
    }
}

fn setup_terminal() -> Result<Terminal<CrosstermBackend<Stdout>>> {
    let mut stdout = io::stdout();
    enable_raw_mode().context("failed to enable raw mode")?;
    execute!(stdout, EnterAlternateScreen).context("unable to enter alternate screen")?;
    Terminal::new(CrosstermBackend::new(stdout)).context("creating terminal failed")
}


fn restore_terminal(terminal: &mut Terminal<CrosstermBackend<Stdout>>) -> Result<()> {
    disable_raw_mode().context("failed to disable raw mode")?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)
        .context("unable to switch to main screen")?;
    terminal.show_cursor().context("unable to show cursor")
}


fn run(terminal: &mut Terminal<CrosstermBackend<Stdout>>, app: &mut App) -> Result<()> {

    const BASE: u32 = 0x40050000;
	const SIZE: u32 = 8;
	const PID: u16 = 0x5bf0;

	let mem = fpga_mem::FpgaMem::new(PID,BASE,SIZE);

    fetch(&mem,app);

    loop {

        terminal.draw(|f| crate::render_app(f,app))?;

        
        if let Event::Key(key) = event::read()? {
            if key.kind == KeyEventKind::Press {
                match key.code {
                    KeyCode::Char('q') => break,
                    KeyCode::Char('n') => do_debug(&mem,app),
                    KeyCode::Enter => {app.mod_register = !app.mod_register;
                                        if(app.mod_register){app.register_input.clear();}
                                        if(!app.mod_register && app.register_input.len()>0)
                                            {push(&mem,app,app.tab_idx,app.register_input.clone());
                                            fetch(&mem,app);}},
                    KeyCode::Backspace => if(app.mod_register){app.register_input.pop();},
                    KeyCode::Esc => if(app.mod_register){app.mod_register = !app.mod_register;},
                    KeyCode::Up => if(app.tab_idx > 0) {app.tab_idx-=1},
                    KeyCode::Down => if(app.tab_idx < app.symbol_table.len()-1) {app.tab_idx+=1},
                    KeyCode::Right => if(app.symbol_table[app.tab_idx].len() > 15){if(app.tab_offset[app.tab_idx] < app.symbol_table[app.tab_idx].len()-15)
                            {app.tab_offset[app.tab_idx]+=1}},
                    KeyCode::Left => if(app.tab_offset[app.tab_idx] > 0){app.tab_offset[app.tab_idx]-=1},
                    KeyCode::Char(to_insert) => {
                        if app.mod_register && to_insert.is_digit(10) {
                            app.enter_char(to_insert);
                        }
                    },
                    KeyCode::Char(to_insert) => {
                        if app.mod_register {
                            app.enter_char(to_insert);
                        }
                    },
                    _ => {}
                }
            }
        }
        
    }
    Ok(())
}

fn list_items(items: Vec<&str>) -> Vec<ListItem> {
    items.iter().map(|i| ListItem::new(i.to_string())).collect()
}


fn render_app(frame: &mut ratatui::Frame<CrosstermBackend<Stdout>>, app: &mut App) {


    
    let chunks = Layout::default()
    .direction(Direction::Horizontal)
    .margin(2)
    .constraints(
        [
            Constraint::Percentage(25),
            Constraint::Percentage(25),
            Constraint::Percentage(25),
            Constraint::Percentage(25),
        ]
        .as_ref(),
    )
    .split(frame.size());

    
    //closure for creating a titled block
    let panel = |title: String| {
        Block::default()
            .borders(Borders::ALL)
            .style(Style::default().bg(Color::Black))
            .border_style(Style::default().fg(Color::White))
            .border_type(BorderType::Rounded)
            .title(Span::styled(
                title,
                Style::default().add_modifier(Modifier::BOLD),
            )).title_alignment(Alignment::Center)
    };

    //closure for creating a popup block
    let popup = |title: String| {
        Block::default()
            .borders(Borders::ALL)
            .border_type(BorderType::Double)
            .border_style(Style::default().fg(Color::Blue))
            .style(Style::default().bg(Color::Gray))
            .title(Span::styled(
                title,
                Style::default().add_modifier(Modifier::BOLD),
            )).title_alignment(Alignment::Center)
            .padding(Padding::uniform(20))
    };

    let block = panel("FPGA Debugger".to_string());


    let table = 'table_logic: {
        let mut t_vals = Vec::new();

        for (i,sym) in app.symbol_table.iter().enumerate()
        {

            use substring::Substring;

            let mut item = Vec::new();
            //hacky way to achieve scrolling of long register names

            item.push(Cell::from(app.symbol_table[i].clone().get(app.tab_offset[i]..).expect("REASON").to_string()));

            //change text when editing registers
            if app.mod_register && i==app.tab_idx
            {

                item.push(Cell::from(app.register_input.clone() + "_"));
            }
            else{
                item.push(Cell::from(app.reg_vals[i].clone()));
            }
            
            t_vals.push(Row::new(item).style(Style::default().fg(Color::White)));
            
        }


        Table::new(t_vals)
            // You can set the style of the entire Table.
            .style(Style::default().bg(Color::Black).fg(Color::White))
            // It has an optional header, which is simply a Row always visible at the top.
            .header(
                Row::new(vec!["Name", "Values"])
                    .style(Style::default().add_modifier(Modifier::BOLD).add_modifier(Modifier::UNDERLINED))
                    // If you want some space between the header and the rest of the rows, you can always
                    // specify some margin at the bottom.
                    .bottom_margin(2)
            )
            // As any other widget, a Table can be wrapped in a Block.
            .block(Block::default().title("Registers").borders(Borders::ALL).title_alignment(Alignment::Center))
            // Columns widths are constrained in the same way as Layout...
            .widths(&[Constraint::Length(15), Constraint::Length(10)])
            // ...and they can be separated by a fixed spacing.
            .column_spacing(1)
            // If you wish to highlight a row in any specific way when it is selected...
            .highlight_style(Style::default().add_modifier(Modifier::BOLD).fg(Color::LightRed))
            // ...and potentially show a symbol in front of the selection.
            .highlight_symbol(">>")
    };

    let mut table_state = 'tablestate_logic: {
        let mut tb = TableState::default();
        tb.select(Some(app.tab_idx));
        tb
    };

    'cursor_logic: {
        if app.mod_register {
            app.cursor_x = chunks[0].x + 15 + 4 + app.register_input.len() as u16; //offset for start of second column
            app.cursor_y = chunks[0].y + app.tab_idx as u16 + 4; //offset for start of rows
            frame.set_cursor(app.cursor_x,app.cursor_y);
        }
        
    }

    

    /*
    if app.mod_register
    {
        let input_panel = popup("Write to register");
        let area = centered_rect(30, 10, frame.size());
        frame.render_widget(Clear,area);
        frame.render_widget(input_panel,area);
    }
    */

    'render_login: {
        frame.render_stateful_widget(table, chunks[0], &mut table_state);
        frame.render_widget(block,frame.size());
    }
    

    
}

/// helper function to create a centered rect using up certain percentage of the available rect `r`
fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints(
            [
                Constraint::Percentage((100 - percent_y) / 2),
                Constraint::Percentage(percent_y),
                Constraint::Percentage((100 - percent_y) / 2),
            ]
            .as_ref(),
        )
        .split(r);

    Layout::default()
        .direction(Direction::Horizontal)
        .constraints(
            [
                Constraint::Percentage((100 - percent_x) / 2),
                Constraint::Percentage(percent_x),
                Constraint::Percentage((100 - percent_x) / 2),
            ]
            .as_ref(),
        )
        .split(popup_layout[1])[1]
}