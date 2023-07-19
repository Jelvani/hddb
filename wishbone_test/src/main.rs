

const DIM: usize = 32;

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
			self.bridge.poke(self.base + index*4,val).unwrap();
		}
	}

	//had trouble implementing this due to return value borrowing data as mutable
	/*
	use std::ops::{Index};

	impl Index<usize> for FpgaMem {
		type Output = u32;
		fn index(&self, index: usize) -> &Self::Output {
			self.mem[index] = self.bridge.peek(self.base + (index as u32)).unwrap();
			&self.mem[index]
		}
	}
	*/
}


use rand::Rng;
use kdam::tqdm;
#[allow(dead_code)]
fn mem_test(mem: fpga_mem::FpgaMem) {
	let mut rng = rand::thread_rng();
	let mut truth: Vec<u32> = vec![0;mem.len as usize];

	println!("Writing rand values");
	for idx in tqdm!(0..(mem.len as usize)) {
		let r: u32 = rng.gen();
		truth[idx] = r;
		mem.set(idx as u32,r);
	}

	println!("Checking rand values");
	for idx in tqdm!(0..(mem.len as usize)) {
		assert!(mem.get(idx as u32) == truth[idx], "Got: {}, Truth: {}",
		mem.get(idx as u32), truth[idx]);
	}

	println!("Check passed!");

}

#[allow(dead_code)]
fn dot_prod(mem: &fpga_mem::FpgaMem, v1: &[u32], v2: &[u32]) -> u32 {
	for i in 0..v1.len(){
		mem.set((i+2) as u32,v1[i]);

	}

	for i in 0..v2.len(){
		mem.set(((i+2+v2.len()) as u32),v2[i]);
	}

	mem.set(1,0x4);

	mem.get(0)
}

#[allow(dead_code)]
fn element_ops(mem: &fpga_mem::FpgaMem, v1: &[u32], v2: &[u32], ops: u32) -> Vec<u32> {
	for i in 0..v1.len(){
		mem.set((i+2) as u32,v1[i]);
	}

	for i in 0..v2.len(){
		mem.set(((i+2+v2.len()) as u32),v2[i]);
	}

	mem.set(1,ops);

	let mut res: Vec<u32> = vec![0; DIM];
	for i in 0..DIM{
		res[i] = mem.get((i+2) as u32);
	}

	
	res
	
}

fn main() {

	const BASE: u32 = 0x40030000;
	const SIZE: u32 = 16*1024;
	const PID: u16 = 0x5bf0;

	const ADD: u32 = 0x1;
	const SUB: u32 = 0x2;
	const MUL: u32 = 0x3;
	const DP: u32 = 0x4;
	
	println!("starting!");
	let mem = fpga_mem::FpgaMem::new(PID,BASE,SIZE);
	//mem_test(mem);

	let v1: [u32; DIM] = [42;DIM];
	let v2: [u32; DIM] = [37;DIM];

	let res = dot_prod(&mem,&v1,&v2);
	let truth: u32 = v1.iter().zip(v2.iter()).map(|(x, y)| x * y).sum();
	println!("DP, Got: {}, Truth: {}", res, truth);

	let mut res2 = element_ops(&mem,&v1,&v2,ADD);
	let mut truth2: Vec<u32> = v1.iter().zip(v2.iter()).map(|(&b, &v)| b+v).collect();
	assert!(res2==truth2);
	println!("ADD, Got: {:?}, Truth: {:?}", res2, truth2);

	res2 = element_ops(&mem,&v1,&v2,MUL);
	truth2 = v1.iter().zip(v2.iter()).map(|(&b, &v)| b*v).collect();
	assert!(res2==truth2);
	println!("MUL, Got: {:?}, Truth: {:?}", res2, truth2);


}
