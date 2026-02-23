// globals.h
#ifndef GLOBALS_H
#define GLOBALS_H

#include <math.h>

extern Double_t mD;
extern Double_t mP;
extern Double_t Ek;
extern Double_t ED;
extern Double_t pD;
extern Double_t beta;
extern Double_t gamma_me;
extern Double_t EDCM;
extern Double_t PDCM;
extern Double_t EPCM;

extern Double_t t_beamline ;// 30 minute
// 厚度 10000 g/m^2 = 1000 mg/cm^2
extern Double_t d_ch2;
// 聚乙烯摩尔质量g/mol
extern Double_t MCH2;
extern Double_t NA;
// 束流 安培 
extern Double_t I;
extern Double_t e_q;



extern Double_t theta_p1_labdeg;
extern Double_t theta_p2_labdeg;
extern Double_t distance_p;
extern Double_t width_p1;
extern Double_t width_p2;

extern Double_t width_p1; //theta p lab width
extern Double_t width_p2; //theta p lab width
extern Double_t width_p1_phi; //theta p cm width
extern Double_t width_p2_phi; //theta p cm width



extern Double_t theta_D_scin_labdeg;
extern Double_t distance_D;
extern Double_t width_D;


void initializeGlobals();

#endif // GLOBALS_H