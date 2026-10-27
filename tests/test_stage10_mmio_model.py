# SPDX-License-Identifier: MIT
"""Execute the historical C helper against fake memory; never access hardware."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stage10',ROOT/'scripts/research/sba6d_stage10_clean_patch.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
PRE=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
typedef uint32_t u32;
struct soc { unsigned caps; }; struct mtk_eth { struct soc *soc; void *dev; };
#define MTK_SOC_MT6990 1
#define MTK_HAS_CAPS(a,b) ((a)&(b))
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,y) ((x)=(y))
static u32 regs[0x6000/4]; static int writes,barriers,warnings,drop;
static u32 mtk_r32(struct mtk_eth *e,unsigned a){(void)e;assert(a<0x6000&&!(a&3));return regs[a/4];}
static void mtk_w32(struct mtk_eth *e,u32 v,unsigned a){(void)e;assert(a<0x6000&&!(a&3));writes++; if(!drop)regs[a/4]=v;}
#define wmb() (++barriers)
#define dev_warn(...) (++warnings)
'''
POST=r'''
static void seed(void){
 memset(regs,0,sizeof(regs));writes=barriers=warnings=drop=0;sbat6d_med_boot_restored=false;
 regs[0x5900/4]=0x1000;regs[0x5904/4]=0x70e4;
 regs[0x5500/4]=0x2000;regs[0x5504/4]=4200;
 regs[0x5510/4]=0x3000;regs[0x5514/4]=4200;
 regs[0x5400/4]=0x4000;regs[0x5404/4]=12150;
 regs[0x5650/4]=regs[0x5628/4]=0x30000;regs[0x5a28/4]=0x80000000;
 regs[0x5a04/4]=0x40002004;regs[0x5604/4]=0x10804825;regs[0x1644/4]=6;
}
int main(void){
 struct soc soc={1};struct mtk_eth eth={&soc,0};struct sbat6d_med_boot_regs s={0};
 seed();sbat6d_med_boot_capture(&eth,&s);assert(s.restore);memset(regs,0,sizeof(regs));
 sbat6d_med_boot_restore(&eth,&s);assert(sbat6d_med_boot_restored&&writes==24&&barriers==1);
 assert(regs[0x5500/4]==0x2000&&regs[0x1644/4]==6&&regs[0x1664/4]==0);
 s=(struct sbat6d_med_boot_regs){0};sbat6d_med_boot_capture(&eth,&s);assert(!s.restore);
 for(int i=0;i<6;i++){
 seed();unsigned offsets[]={0x5904,0x5504,0x5514,0x5404,0x5628,0x5650};regs[offsets[i]/4]^=1;
 s=(struct sbat6d_med_boot_regs){0};sbat6d_med_boot_capture(&eth,&s);assert(!s.restore);
 memset(regs,0,sizeof(regs));sbat6d_med_boot_restore(&eth,&s);assert(writes==0);
 }
 seed();soc.caps=0;s=(struct sbat6d_med_boot_regs){0};sbat6d_med_boot_capture(&eth,&s);assert(!s.restore);soc.caps=1;
 seed();s=(struct sbat6d_med_boot_regs){0};sbat6d_med_boot_capture(&eth,&s);sbat6d_med_boot_restore(&eth,&s);assert(!writes);
 seed();s=(struct sbat6d_med_boot_regs){0};sbat6d_med_boot_capture(&eth,&s);memset(regs,0,sizeof(regs));drop=1;
 sbat6d_med_boot_restore(&eth,&s);assert(!sbat6d_med_boot_restored&&warnings==1);
 puts("11 fake-MMIO scenarios passed");return 0;
}
'''
class FakeMMIO(unittest.TestCase):
 def test_actual_helper(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'fixture.c').write_text(PRE+m.HELPER+POST)
   subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(p/'fixture.c'),'-o',str(p/'fixture')],check=True)
   subprocess.run([str(p/'fixture')],check=True)
if __name__=='__main__':unittest.main()
