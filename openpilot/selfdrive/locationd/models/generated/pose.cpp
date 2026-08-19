#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_6785328779902013998) {
   out_6785328779902013998[0] = delta_x[0] + nom_x[0];
   out_6785328779902013998[1] = delta_x[1] + nom_x[1];
   out_6785328779902013998[2] = delta_x[2] + nom_x[2];
   out_6785328779902013998[3] = delta_x[3] + nom_x[3];
   out_6785328779902013998[4] = delta_x[4] + nom_x[4];
   out_6785328779902013998[5] = delta_x[5] + nom_x[5];
   out_6785328779902013998[6] = delta_x[6] + nom_x[6];
   out_6785328779902013998[7] = delta_x[7] + nom_x[7];
   out_6785328779902013998[8] = delta_x[8] + nom_x[8];
   out_6785328779902013998[9] = delta_x[9] + nom_x[9];
   out_6785328779902013998[10] = delta_x[10] + nom_x[10];
   out_6785328779902013998[11] = delta_x[11] + nom_x[11];
   out_6785328779902013998[12] = delta_x[12] + nom_x[12];
   out_6785328779902013998[13] = delta_x[13] + nom_x[13];
   out_6785328779902013998[14] = delta_x[14] + nom_x[14];
   out_6785328779902013998[15] = delta_x[15] + nom_x[15];
   out_6785328779902013998[16] = delta_x[16] + nom_x[16];
   out_6785328779902013998[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2829352640446112927) {
   out_2829352640446112927[0] = -nom_x[0] + true_x[0];
   out_2829352640446112927[1] = -nom_x[1] + true_x[1];
   out_2829352640446112927[2] = -nom_x[2] + true_x[2];
   out_2829352640446112927[3] = -nom_x[3] + true_x[3];
   out_2829352640446112927[4] = -nom_x[4] + true_x[4];
   out_2829352640446112927[5] = -nom_x[5] + true_x[5];
   out_2829352640446112927[6] = -nom_x[6] + true_x[6];
   out_2829352640446112927[7] = -nom_x[7] + true_x[7];
   out_2829352640446112927[8] = -nom_x[8] + true_x[8];
   out_2829352640446112927[9] = -nom_x[9] + true_x[9];
   out_2829352640446112927[10] = -nom_x[10] + true_x[10];
   out_2829352640446112927[11] = -nom_x[11] + true_x[11];
   out_2829352640446112927[12] = -nom_x[12] + true_x[12];
   out_2829352640446112927[13] = -nom_x[13] + true_x[13];
   out_2829352640446112927[14] = -nom_x[14] + true_x[14];
   out_2829352640446112927[15] = -nom_x[15] + true_x[15];
   out_2829352640446112927[16] = -nom_x[16] + true_x[16];
   out_2829352640446112927[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_8987481613780806210) {
   out_8987481613780806210[0] = 1.0;
   out_8987481613780806210[1] = 0.0;
   out_8987481613780806210[2] = 0.0;
   out_8987481613780806210[3] = 0.0;
   out_8987481613780806210[4] = 0.0;
   out_8987481613780806210[5] = 0.0;
   out_8987481613780806210[6] = 0.0;
   out_8987481613780806210[7] = 0.0;
   out_8987481613780806210[8] = 0.0;
   out_8987481613780806210[9] = 0.0;
   out_8987481613780806210[10] = 0.0;
   out_8987481613780806210[11] = 0.0;
   out_8987481613780806210[12] = 0.0;
   out_8987481613780806210[13] = 0.0;
   out_8987481613780806210[14] = 0.0;
   out_8987481613780806210[15] = 0.0;
   out_8987481613780806210[16] = 0.0;
   out_8987481613780806210[17] = 0.0;
   out_8987481613780806210[18] = 0.0;
   out_8987481613780806210[19] = 1.0;
   out_8987481613780806210[20] = 0.0;
   out_8987481613780806210[21] = 0.0;
   out_8987481613780806210[22] = 0.0;
   out_8987481613780806210[23] = 0.0;
   out_8987481613780806210[24] = 0.0;
   out_8987481613780806210[25] = 0.0;
   out_8987481613780806210[26] = 0.0;
   out_8987481613780806210[27] = 0.0;
   out_8987481613780806210[28] = 0.0;
   out_8987481613780806210[29] = 0.0;
   out_8987481613780806210[30] = 0.0;
   out_8987481613780806210[31] = 0.0;
   out_8987481613780806210[32] = 0.0;
   out_8987481613780806210[33] = 0.0;
   out_8987481613780806210[34] = 0.0;
   out_8987481613780806210[35] = 0.0;
   out_8987481613780806210[36] = 0.0;
   out_8987481613780806210[37] = 0.0;
   out_8987481613780806210[38] = 1.0;
   out_8987481613780806210[39] = 0.0;
   out_8987481613780806210[40] = 0.0;
   out_8987481613780806210[41] = 0.0;
   out_8987481613780806210[42] = 0.0;
   out_8987481613780806210[43] = 0.0;
   out_8987481613780806210[44] = 0.0;
   out_8987481613780806210[45] = 0.0;
   out_8987481613780806210[46] = 0.0;
   out_8987481613780806210[47] = 0.0;
   out_8987481613780806210[48] = 0.0;
   out_8987481613780806210[49] = 0.0;
   out_8987481613780806210[50] = 0.0;
   out_8987481613780806210[51] = 0.0;
   out_8987481613780806210[52] = 0.0;
   out_8987481613780806210[53] = 0.0;
   out_8987481613780806210[54] = 0.0;
   out_8987481613780806210[55] = 0.0;
   out_8987481613780806210[56] = 0.0;
   out_8987481613780806210[57] = 1.0;
   out_8987481613780806210[58] = 0.0;
   out_8987481613780806210[59] = 0.0;
   out_8987481613780806210[60] = 0.0;
   out_8987481613780806210[61] = 0.0;
   out_8987481613780806210[62] = 0.0;
   out_8987481613780806210[63] = 0.0;
   out_8987481613780806210[64] = 0.0;
   out_8987481613780806210[65] = 0.0;
   out_8987481613780806210[66] = 0.0;
   out_8987481613780806210[67] = 0.0;
   out_8987481613780806210[68] = 0.0;
   out_8987481613780806210[69] = 0.0;
   out_8987481613780806210[70] = 0.0;
   out_8987481613780806210[71] = 0.0;
   out_8987481613780806210[72] = 0.0;
   out_8987481613780806210[73] = 0.0;
   out_8987481613780806210[74] = 0.0;
   out_8987481613780806210[75] = 0.0;
   out_8987481613780806210[76] = 1.0;
   out_8987481613780806210[77] = 0.0;
   out_8987481613780806210[78] = 0.0;
   out_8987481613780806210[79] = 0.0;
   out_8987481613780806210[80] = 0.0;
   out_8987481613780806210[81] = 0.0;
   out_8987481613780806210[82] = 0.0;
   out_8987481613780806210[83] = 0.0;
   out_8987481613780806210[84] = 0.0;
   out_8987481613780806210[85] = 0.0;
   out_8987481613780806210[86] = 0.0;
   out_8987481613780806210[87] = 0.0;
   out_8987481613780806210[88] = 0.0;
   out_8987481613780806210[89] = 0.0;
   out_8987481613780806210[90] = 0.0;
   out_8987481613780806210[91] = 0.0;
   out_8987481613780806210[92] = 0.0;
   out_8987481613780806210[93] = 0.0;
   out_8987481613780806210[94] = 0.0;
   out_8987481613780806210[95] = 1.0;
   out_8987481613780806210[96] = 0.0;
   out_8987481613780806210[97] = 0.0;
   out_8987481613780806210[98] = 0.0;
   out_8987481613780806210[99] = 0.0;
   out_8987481613780806210[100] = 0.0;
   out_8987481613780806210[101] = 0.0;
   out_8987481613780806210[102] = 0.0;
   out_8987481613780806210[103] = 0.0;
   out_8987481613780806210[104] = 0.0;
   out_8987481613780806210[105] = 0.0;
   out_8987481613780806210[106] = 0.0;
   out_8987481613780806210[107] = 0.0;
   out_8987481613780806210[108] = 0.0;
   out_8987481613780806210[109] = 0.0;
   out_8987481613780806210[110] = 0.0;
   out_8987481613780806210[111] = 0.0;
   out_8987481613780806210[112] = 0.0;
   out_8987481613780806210[113] = 0.0;
   out_8987481613780806210[114] = 1.0;
   out_8987481613780806210[115] = 0.0;
   out_8987481613780806210[116] = 0.0;
   out_8987481613780806210[117] = 0.0;
   out_8987481613780806210[118] = 0.0;
   out_8987481613780806210[119] = 0.0;
   out_8987481613780806210[120] = 0.0;
   out_8987481613780806210[121] = 0.0;
   out_8987481613780806210[122] = 0.0;
   out_8987481613780806210[123] = 0.0;
   out_8987481613780806210[124] = 0.0;
   out_8987481613780806210[125] = 0.0;
   out_8987481613780806210[126] = 0.0;
   out_8987481613780806210[127] = 0.0;
   out_8987481613780806210[128] = 0.0;
   out_8987481613780806210[129] = 0.0;
   out_8987481613780806210[130] = 0.0;
   out_8987481613780806210[131] = 0.0;
   out_8987481613780806210[132] = 0.0;
   out_8987481613780806210[133] = 1.0;
   out_8987481613780806210[134] = 0.0;
   out_8987481613780806210[135] = 0.0;
   out_8987481613780806210[136] = 0.0;
   out_8987481613780806210[137] = 0.0;
   out_8987481613780806210[138] = 0.0;
   out_8987481613780806210[139] = 0.0;
   out_8987481613780806210[140] = 0.0;
   out_8987481613780806210[141] = 0.0;
   out_8987481613780806210[142] = 0.0;
   out_8987481613780806210[143] = 0.0;
   out_8987481613780806210[144] = 0.0;
   out_8987481613780806210[145] = 0.0;
   out_8987481613780806210[146] = 0.0;
   out_8987481613780806210[147] = 0.0;
   out_8987481613780806210[148] = 0.0;
   out_8987481613780806210[149] = 0.0;
   out_8987481613780806210[150] = 0.0;
   out_8987481613780806210[151] = 0.0;
   out_8987481613780806210[152] = 1.0;
   out_8987481613780806210[153] = 0.0;
   out_8987481613780806210[154] = 0.0;
   out_8987481613780806210[155] = 0.0;
   out_8987481613780806210[156] = 0.0;
   out_8987481613780806210[157] = 0.0;
   out_8987481613780806210[158] = 0.0;
   out_8987481613780806210[159] = 0.0;
   out_8987481613780806210[160] = 0.0;
   out_8987481613780806210[161] = 0.0;
   out_8987481613780806210[162] = 0.0;
   out_8987481613780806210[163] = 0.0;
   out_8987481613780806210[164] = 0.0;
   out_8987481613780806210[165] = 0.0;
   out_8987481613780806210[166] = 0.0;
   out_8987481613780806210[167] = 0.0;
   out_8987481613780806210[168] = 0.0;
   out_8987481613780806210[169] = 0.0;
   out_8987481613780806210[170] = 0.0;
   out_8987481613780806210[171] = 1.0;
   out_8987481613780806210[172] = 0.0;
   out_8987481613780806210[173] = 0.0;
   out_8987481613780806210[174] = 0.0;
   out_8987481613780806210[175] = 0.0;
   out_8987481613780806210[176] = 0.0;
   out_8987481613780806210[177] = 0.0;
   out_8987481613780806210[178] = 0.0;
   out_8987481613780806210[179] = 0.0;
   out_8987481613780806210[180] = 0.0;
   out_8987481613780806210[181] = 0.0;
   out_8987481613780806210[182] = 0.0;
   out_8987481613780806210[183] = 0.0;
   out_8987481613780806210[184] = 0.0;
   out_8987481613780806210[185] = 0.0;
   out_8987481613780806210[186] = 0.0;
   out_8987481613780806210[187] = 0.0;
   out_8987481613780806210[188] = 0.0;
   out_8987481613780806210[189] = 0.0;
   out_8987481613780806210[190] = 1.0;
   out_8987481613780806210[191] = 0.0;
   out_8987481613780806210[192] = 0.0;
   out_8987481613780806210[193] = 0.0;
   out_8987481613780806210[194] = 0.0;
   out_8987481613780806210[195] = 0.0;
   out_8987481613780806210[196] = 0.0;
   out_8987481613780806210[197] = 0.0;
   out_8987481613780806210[198] = 0.0;
   out_8987481613780806210[199] = 0.0;
   out_8987481613780806210[200] = 0.0;
   out_8987481613780806210[201] = 0.0;
   out_8987481613780806210[202] = 0.0;
   out_8987481613780806210[203] = 0.0;
   out_8987481613780806210[204] = 0.0;
   out_8987481613780806210[205] = 0.0;
   out_8987481613780806210[206] = 0.0;
   out_8987481613780806210[207] = 0.0;
   out_8987481613780806210[208] = 0.0;
   out_8987481613780806210[209] = 1.0;
   out_8987481613780806210[210] = 0.0;
   out_8987481613780806210[211] = 0.0;
   out_8987481613780806210[212] = 0.0;
   out_8987481613780806210[213] = 0.0;
   out_8987481613780806210[214] = 0.0;
   out_8987481613780806210[215] = 0.0;
   out_8987481613780806210[216] = 0.0;
   out_8987481613780806210[217] = 0.0;
   out_8987481613780806210[218] = 0.0;
   out_8987481613780806210[219] = 0.0;
   out_8987481613780806210[220] = 0.0;
   out_8987481613780806210[221] = 0.0;
   out_8987481613780806210[222] = 0.0;
   out_8987481613780806210[223] = 0.0;
   out_8987481613780806210[224] = 0.0;
   out_8987481613780806210[225] = 0.0;
   out_8987481613780806210[226] = 0.0;
   out_8987481613780806210[227] = 0.0;
   out_8987481613780806210[228] = 1.0;
   out_8987481613780806210[229] = 0.0;
   out_8987481613780806210[230] = 0.0;
   out_8987481613780806210[231] = 0.0;
   out_8987481613780806210[232] = 0.0;
   out_8987481613780806210[233] = 0.0;
   out_8987481613780806210[234] = 0.0;
   out_8987481613780806210[235] = 0.0;
   out_8987481613780806210[236] = 0.0;
   out_8987481613780806210[237] = 0.0;
   out_8987481613780806210[238] = 0.0;
   out_8987481613780806210[239] = 0.0;
   out_8987481613780806210[240] = 0.0;
   out_8987481613780806210[241] = 0.0;
   out_8987481613780806210[242] = 0.0;
   out_8987481613780806210[243] = 0.0;
   out_8987481613780806210[244] = 0.0;
   out_8987481613780806210[245] = 0.0;
   out_8987481613780806210[246] = 0.0;
   out_8987481613780806210[247] = 1.0;
   out_8987481613780806210[248] = 0.0;
   out_8987481613780806210[249] = 0.0;
   out_8987481613780806210[250] = 0.0;
   out_8987481613780806210[251] = 0.0;
   out_8987481613780806210[252] = 0.0;
   out_8987481613780806210[253] = 0.0;
   out_8987481613780806210[254] = 0.0;
   out_8987481613780806210[255] = 0.0;
   out_8987481613780806210[256] = 0.0;
   out_8987481613780806210[257] = 0.0;
   out_8987481613780806210[258] = 0.0;
   out_8987481613780806210[259] = 0.0;
   out_8987481613780806210[260] = 0.0;
   out_8987481613780806210[261] = 0.0;
   out_8987481613780806210[262] = 0.0;
   out_8987481613780806210[263] = 0.0;
   out_8987481613780806210[264] = 0.0;
   out_8987481613780806210[265] = 0.0;
   out_8987481613780806210[266] = 1.0;
   out_8987481613780806210[267] = 0.0;
   out_8987481613780806210[268] = 0.0;
   out_8987481613780806210[269] = 0.0;
   out_8987481613780806210[270] = 0.0;
   out_8987481613780806210[271] = 0.0;
   out_8987481613780806210[272] = 0.0;
   out_8987481613780806210[273] = 0.0;
   out_8987481613780806210[274] = 0.0;
   out_8987481613780806210[275] = 0.0;
   out_8987481613780806210[276] = 0.0;
   out_8987481613780806210[277] = 0.0;
   out_8987481613780806210[278] = 0.0;
   out_8987481613780806210[279] = 0.0;
   out_8987481613780806210[280] = 0.0;
   out_8987481613780806210[281] = 0.0;
   out_8987481613780806210[282] = 0.0;
   out_8987481613780806210[283] = 0.0;
   out_8987481613780806210[284] = 0.0;
   out_8987481613780806210[285] = 1.0;
   out_8987481613780806210[286] = 0.0;
   out_8987481613780806210[287] = 0.0;
   out_8987481613780806210[288] = 0.0;
   out_8987481613780806210[289] = 0.0;
   out_8987481613780806210[290] = 0.0;
   out_8987481613780806210[291] = 0.0;
   out_8987481613780806210[292] = 0.0;
   out_8987481613780806210[293] = 0.0;
   out_8987481613780806210[294] = 0.0;
   out_8987481613780806210[295] = 0.0;
   out_8987481613780806210[296] = 0.0;
   out_8987481613780806210[297] = 0.0;
   out_8987481613780806210[298] = 0.0;
   out_8987481613780806210[299] = 0.0;
   out_8987481613780806210[300] = 0.0;
   out_8987481613780806210[301] = 0.0;
   out_8987481613780806210[302] = 0.0;
   out_8987481613780806210[303] = 0.0;
   out_8987481613780806210[304] = 1.0;
   out_8987481613780806210[305] = 0.0;
   out_8987481613780806210[306] = 0.0;
   out_8987481613780806210[307] = 0.0;
   out_8987481613780806210[308] = 0.0;
   out_8987481613780806210[309] = 0.0;
   out_8987481613780806210[310] = 0.0;
   out_8987481613780806210[311] = 0.0;
   out_8987481613780806210[312] = 0.0;
   out_8987481613780806210[313] = 0.0;
   out_8987481613780806210[314] = 0.0;
   out_8987481613780806210[315] = 0.0;
   out_8987481613780806210[316] = 0.0;
   out_8987481613780806210[317] = 0.0;
   out_8987481613780806210[318] = 0.0;
   out_8987481613780806210[319] = 0.0;
   out_8987481613780806210[320] = 0.0;
   out_8987481613780806210[321] = 0.0;
   out_8987481613780806210[322] = 0.0;
   out_8987481613780806210[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_4410802230801501271) {
   out_4410802230801501271[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_4410802230801501271[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_4410802230801501271[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_4410802230801501271[3] = dt*state[12] + state[3];
   out_4410802230801501271[4] = dt*state[13] + state[4];
   out_4410802230801501271[5] = dt*state[14] + state[5];
   out_4410802230801501271[6] = state[6];
   out_4410802230801501271[7] = state[7];
   out_4410802230801501271[8] = state[8];
   out_4410802230801501271[9] = state[9];
   out_4410802230801501271[10] = state[10];
   out_4410802230801501271[11] = state[11];
   out_4410802230801501271[12] = state[12];
   out_4410802230801501271[13] = state[13];
   out_4410802230801501271[14] = state[14];
   out_4410802230801501271[15] = state[15];
   out_4410802230801501271[16] = state[16];
   out_4410802230801501271[17] = state[17];
}
void F_fun(double *state, double dt, double *out_2018795142748431206) {
   out_2018795142748431206[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2018795142748431206[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2018795142748431206[2] = 0;
   out_2018795142748431206[3] = 0;
   out_2018795142748431206[4] = 0;
   out_2018795142748431206[5] = 0;
   out_2018795142748431206[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2018795142748431206[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2018795142748431206[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2018795142748431206[9] = 0;
   out_2018795142748431206[10] = 0;
   out_2018795142748431206[11] = 0;
   out_2018795142748431206[12] = 0;
   out_2018795142748431206[13] = 0;
   out_2018795142748431206[14] = 0;
   out_2018795142748431206[15] = 0;
   out_2018795142748431206[16] = 0;
   out_2018795142748431206[17] = 0;
   out_2018795142748431206[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2018795142748431206[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2018795142748431206[20] = 0;
   out_2018795142748431206[21] = 0;
   out_2018795142748431206[22] = 0;
   out_2018795142748431206[23] = 0;
   out_2018795142748431206[24] = 0;
   out_2018795142748431206[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2018795142748431206[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2018795142748431206[27] = 0;
   out_2018795142748431206[28] = 0;
   out_2018795142748431206[29] = 0;
   out_2018795142748431206[30] = 0;
   out_2018795142748431206[31] = 0;
   out_2018795142748431206[32] = 0;
   out_2018795142748431206[33] = 0;
   out_2018795142748431206[34] = 0;
   out_2018795142748431206[35] = 0;
   out_2018795142748431206[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2018795142748431206[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2018795142748431206[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2018795142748431206[39] = 0;
   out_2018795142748431206[40] = 0;
   out_2018795142748431206[41] = 0;
   out_2018795142748431206[42] = 0;
   out_2018795142748431206[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2018795142748431206[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2018795142748431206[45] = 0;
   out_2018795142748431206[46] = 0;
   out_2018795142748431206[47] = 0;
   out_2018795142748431206[48] = 0;
   out_2018795142748431206[49] = 0;
   out_2018795142748431206[50] = 0;
   out_2018795142748431206[51] = 0;
   out_2018795142748431206[52] = 0;
   out_2018795142748431206[53] = 0;
   out_2018795142748431206[54] = 0;
   out_2018795142748431206[55] = 0;
   out_2018795142748431206[56] = 0;
   out_2018795142748431206[57] = 1;
   out_2018795142748431206[58] = 0;
   out_2018795142748431206[59] = 0;
   out_2018795142748431206[60] = 0;
   out_2018795142748431206[61] = 0;
   out_2018795142748431206[62] = 0;
   out_2018795142748431206[63] = 0;
   out_2018795142748431206[64] = 0;
   out_2018795142748431206[65] = 0;
   out_2018795142748431206[66] = dt;
   out_2018795142748431206[67] = 0;
   out_2018795142748431206[68] = 0;
   out_2018795142748431206[69] = 0;
   out_2018795142748431206[70] = 0;
   out_2018795142748431206[71] = 0;
   out_2018795142748431206[72] = 0;
   out_2018795142748431206[73] = 0;
   out_2018795142748431206[74] = 0;
   out_2018795142748431206[75] = 0;
   out_2018795142748431206[76] = 1;
   out_2018795142748431206[77] = 0;
   out_2018795142748431206[78] = 0;
   out_2018795142748431206[79] = 0;
   out_2018795142748431206[80] = 0;
   out_2018795142748431206[81] = 0;
   out_2018795142748431206[82] = 0;
   out_2018795142748431206[83] = 0;
   out_2018795142748431206[84] = 0;
   out_2018795142748431206[85] = dt;
   out_2018795142748431206[86] = 0;
   out_2018795142748431206[87] = 0;
   out_2018795142748431206[88] = 0;
   out_2018795142748431206[89] = 0;
   out_2018795142748431206[90] = 0;
   out_2018795142748431206[91] = 0;
   out_2018795142748431206[92] = 0;
   out_2018795142748431206[93] = 0;
   out_2018795142748431206[94] = 0;
   out_2018795142748431206[95] = 1;
   out_2018795142748431206[96] = 0;
   out_2018795142748431206[97] = 0;
   out_2018795142748431206[98] = 0;
   out_2018795142748431206[99] = 0;
   out_2018795142748431206[100] = 0;
   out_2018795142748431206[101] = 0;
   out_2018795142748431206[102] = 0;
   out_2018795142748431206[103] = 0;
   out_2018795142748431206[104] = dt;
   out_2018795142748431206[105] = 0;
   out_2018795142748431206[106] = 0;
   out_2018795142748431206[107] = 0;
   out_2018795142748431206[108] = 0;
   out_2018795142748431206[109] = 0;
   out_2018795142748431206[110] = 0;
   out_2018795142748431206[111] = 0;
   out_2018795142748431206[112] = 0;
   out_2018795142748431206[113] = 0;
   out_2018795142748431206[114] = 1;
   out_2018795142748431206[115] = 0;
   out_2018795142748431206[116] = 0;
   out_2018795142748431206[117] = 0;
   out_2018795142748431206[118] = 0;
   out_2018795142748431206[119] = 0;
   out_2018795142748431206[120] = 0;
   out_2018795142748431206[121] = 0;
   out_2018795142748431206[122] = 0;
   out_2018795142748431206[123] = 0;
   out_2018795142748431206[124] = 0;
   out_2018795142748431206[125] = 0;
   out_2018795142748431206[126] = 0;
   out_2018795142748431206[127] = 0;
   out_2018795142748431206[128] = 0;
   out_2018795142748431206[129] = 0;
   out_2018795142748431206[130] = 0;
   out_2018795142748431206[131] = 0;
   out_2018795142748431206[132] = 0;
   out_2018795142748431206[133] = 1;
   out_2018795142748431206[134] = 0;
   out_2018795142748431206[135] = 0;
   out_2018795142748431206[136] = 0;
   out_2018795142748431206[137] = 0;
   out_2018795142748431206[138] = 0;
   out_2018795142748431206[139] = 0;
   out_2018795142748431206[140] = 0;
   out_2018795142748431206[141] = 0;
   out_2018795142748431206[142] = 0;
   out_2018795142748431206[143] = 0;
   out_2018795142748431206[144] = 0;
   out_2018795142748431206[145] = 0;
   out_2018795142748431206[146] = 0;
   out_2018795142748431206[147] = 0;
   out_2018795142748431206[148] = 0;
   out_2018795142748431206[149] = 0;
   out_2018795142748431206[150] = 0;
   out_2018795142748431206[151] = 0;
   out_2018795142748431206[152] = 1;
   out_2018795142748431206[153] = 0;
   out_2018795142748431206[154] = 0;
   out_2018795142748431206[155] = 0;
   out_2018795142748431206[156] = 0;
   out_2018795142748431206[157] = 0;
   out_2018795142748431206[158] = 0;
   out_2018795142748431206[159] = 0;
   out_2018795142748431206[160] = 0;
   out_2018795142748431206[161] = 0;
   out_2018795142748431206[162] = 0;
   out_2018795142748431206[163] = 0;
   out_2018795142748431206[164] = 0;
   out_2018795142748431206[165] = 0;
   out_2018795142748431206[166] = 0;
   out_2018795142748431206[167] = 0;
   out_2018795142748431206[168] = 0;
   out_2018795142748431206[169] = 0;
   out_2018795142748431206[170] = 0;
   out_2018795142748431206[171] = 1;
   out_2018795142748431206[172] = 0;
   out_2018795142748431206[173] = 0;
   out_2018795142748431206[174] = 0;
   out_2018795142748431206[175] = 0;
   out_2018795142748431206[176] = 0;
   out_2018795142748431206[177] = 0;
   out_2018795142748431206[178] = 0;
   out_2018795142748431206[179] = 0;
   out_2018795142748431206[180] = 0;
   out_2018795142748431206[181] = 0;
   out_2018795142748431206[182] = 0;
   out_2018795142748431206[183] = 0;
   out_2018795142748431206[184] = 0;
   out_2018795142748431206[185] = 0;
   out_2018795142748431206[186] = 0;
   out_2018795142748431206[187] = 0;
   out_2018795142748431206[188] = 0;
   out_2018795142748431206[189] = 0;
   out_2018795142748431206[190] = 1;
   out_2018795142748431206[191] = 0;
   out_2018795142748431206[192] = 0;
   out_2018795142748431206[193] = 0;
   out_2018795142748431206[194] = 0;
   out_2018795142748431206[195] = 0;
   out_2018795142748431206[196] = 0;
   out_2018795142748431206[197] = 0;
   out_2018795142748431206[198] = 0;
   out_2018795142748431206[199] = 0;
   out_2018795142748431206[200] = 0;
   out_2018795142748431206[201] = 0;
   out_2018795142748431206[202] = 0;
   out_2018795142748431206[203] = 0;
   out_2018795142748431206[204] = 0;
   out_2018795142748431206[205] = 0;
   out_2018795142748431206[206] = 0;
   out_2018795142748431206[207] = 0;
   out_2018795142748431206[208] = 0;
   out_2018795142748431206[209] = 1;
   out_2018795142748431206[210] = 0;
   out_2018795142748431206[211] = 0;
   out_2018795142748431206[212] = 0;
   out_2018795142748431206[213] = 0;
   out_2018795142748431206[214] = 0;
   out_2018795142748431206[215] = 0;
   out_2018795142748431206[216] = 0;
   out_2018795142748431206[217] = 0;
   out_2018795142748431206[218] = 0;
   out_2018795142748431206[219] = 0;
   out_2018795142748431206[220] = 0;
   out_2018795142748431206[221] = 0;
   out_2018795142748431206[222] = 0;
   out_2018795142748431206[223] = 0;
   out_2018795142748431206[224] = 0;
   out_2018795142748431206[225] = 0;
   out_2018795142748431206[226] = 0;
   out_2018795142748431206[227] = 0;
   out_2018795142748431206[228] = 1;
   out_2018795142748431206[229] = 0;
   out_2018795142748431206[230] = 0;
   out_2018795142748431206[231] = 0;
   out_2018795142748431206[232] = 0;
   out_2018795142748431206[233] = 0;
   out_2018795142748431206[234] = 0;
   out_2018795142748431206[235] = 0;
   out_2018795142748431206[236] = 0;
   out_2018795142748431206[237] = 0;
   out_2018795142748431206[238] = 0;
   out_2018795142748431206[239] = 0;
   out_2018795142748431206[240] = 0;
   out_2018795142748431206[241] = 0;
   out_2018795142748431206[242] = 0;
   out_2018795142748431206[243] = 0;
   out_2018795142748431206[244] = 0;
   out_2018795142748431206[245] = 0;
   out_2018795142748431206[246] = 0;
   out_2018795142748431206[247] = 1;
   out_2018795142748431206[248] = 0;
   out_2018795142748431206[249] = 0;
   out_2018795142748431206[250] = 0;
   out_2018795142748431206[251] = 0;
   out_2018795142748431206[252] = 0;
   out_2018795142748431206[253] = 0;
   out_2018795142748431206[254] = 0;
   out_2018795142748431206[255] = 0;
   out_2018795142748431206[256] = 0;
   out_2018795142748431206[257] = 0;
   out_2018795142748431206[258] = 0;
   out_2018795142748431206[259] = 0;
   out_2018795142748431206[260] = 0;
   out_2018795142748431206[261] = 0;
   out_2018795142748431206[262] = 0;
   out_2018795142748431206[263] = 0;
   out_2018795142748431206[264] = 0;
   out_2018795142748431206[265] = 0;
   out_2018795142748431206[266] = 1;
   out_2018795142748431206[267] = 0;
   out_2018795142748431206[268] = 0;
   out_2018795142748431206[269] = 0;
   out_2018795142748431206[270] = 0;
   out_2018795142748431206[271] = 0;
   out_2018795142748431206[272] = 0;
   out_2018795142748431206[273] = 0;
   out_2018795142748431206[274] = 0;
   out_2018795142748431206[275] = 0;
   out_2018795142748431206[276] = 0;
   out_2018795142748431206[277] = 0;
   out_2018795142748431206[278] = 0;
   out_2018795142748431206[279] = 0;
   out_2018795142748431206[280] = 0;
   out_2018795142748431206[281] = 0;
   out_2018795142748431206[282] = 0;
   out_2018795142748431206[283] = 0;
   out_2018795142748431206[284] = 0;
   out_2018795142748431206[285] = 1;
   out_2018795142748431206[286] = 0;
   out_2018795142748431206[287] = 0;
   out_2018795142748431206[288] = 0;
   out_2018795142748431206[289] = 0;
   out_2018795142748431206[290] = 0;
   out_2018795142748431206[291] = 0;
   out_2018795142748431206[292] = 0;
   out_2018795142748431206[293] = 0;
   out_2018795142748431206[294] = 0;
   out_2018795142748431206[295] = 0;
   out_2018795142748431206[296] = 0;
   out_2018795142748431206[297] = 0;
   out_2018795142748431206[298] = 0;
   out_2018795142748431206[299] = 0;
   out_2018795142748431206[300] = 0;
   out_2018795142748431206[301] = 0;
   out_2018795142748431206[302] = 0;
   out_2018795142748431206[303] = 0;
   out_2018795142748431206[304] = 1;
   out_2018795142748431206[305] = 0;
   out_2018795142748431206[306] = 0;
   out_2018795142748431206[307] = 0;
   out_2018795142748431206[308] = 0;
   out_2018795142748431206[309] = 0;
   out_2018795142748431206[310] = 0;
   out_2018795142748431206[311] = 0;
   out_2018795142748431206[312] = 0;
   out_2018795142748431206[313] = 0;
   out_2018795142748431206[314] = 0;
   out_2018795142748431206[315] = 0;
   out_2018795142748431206[316] = 0;
   out_2018795142748431206[317] = 0;
   out_2018795142748431206[318] = 0;
   out_2018795142748431206[319] = 0;
   out_2018795142748431206[320] = 0;
   out_2018795142748431206[321] = 0;
   out_2018795142748431206[322] = 0;
   out_2018795142748431206[323] = 1;
}
void h_4(double *state, double *unused, double *out_2992805398127947193) {
   out_2992805398127947193[0] = state[6] + state[9];
   out_2992805398127947193[1] = state[7] + state[10];
   out_2992805398127947193[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_514900793870924064) {
   out_514900793870924064[0] = 0;
   out_514900793870924064[1] = 0;
   out_514900793870924064[2] = 0;
   out_514900793870924064[3] = 0;
   out_514900793870924064[4] = 0;
   out_514900793870924064[5] = 0;
   out_514900793870924064[6] = 1;
   out_514900793870924064[7] = 0;
   out_514900793870924064[8] = 0;
   out_514900793870924064[9] = 1;
   out_514900793870924064[10] = 0;
   out_514900793870924064[11] = 0;
   out_514900793870924064[12] = 0;
   out_514900793870924064[13] = 0;
   out_514900793870924064[14] = 0;
   out_514900793870924064[15] = 0;
   out_514900793870924064[16] = 0;
   out_514900793870924064[17] = 0;
   out_514900793870924064[18] = 0;
   out_514900793870924064[19] = 0;
   out_514900793870924064[20] = 0;
   out_514900793870924064[21] = 0;
   out_514900793870924064[22] = 0;
   out_514900793870924064[23] = 0;
   out_514900793870924064[24] = 0;
   out_514900793870924064[25] = 1;
   out_514900793870924064[26] = 0;
   out_514900793870924064[27] = 0;
   out_514900793870924064[28] = 1;
   out_514900793870924064[29] = 0;
   out_514900793870924064[30] = 0;
   out_514900793870924064[31] = 0;
   out_514900793870924064[32] = 0;
   out_514900793870924064[33] = 0;
   out_514900793870924064[34] = 0;
   out_514900793870924064[35] = 0;
   out_514900793870924064[36] = 0;
   out_514900793870924064[37] = 0;
   out_514900793870924064[38] = 0;
   out_514900793870924064[39] = 0;
   out_514900793870924064[40] = 0;
   out_514900793870924064[41] = 0;
   out_514900793870924064[42] = 0;
   out_514900793870924064[43] = 0;
   out_514900793870924064[44] = 1;
   out_514900793870924064[45] = 0;
   out_514900793870924064[46] = 0;
   out_514900793870924064[47] = 1;
   out_514900793870924064[48] = 0;
   out_514900793870924064[49] = 0;
   out_514900793870924064[50] = 0;
   out_514900793870924064[51] = 0;
   out_514900793870924064[52] = 0;
   out_514900793870924064[53] = 0;
}
void h_10(double *state, double *unused, double *out_1631737084541257867) {
   out_1631737084541257867[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_1631737084541257867[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_1631737084541257867[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_8819561164250357809) {
   out_8819561164250357809[0] = 0;
   out_8819561164250357809[1] = 9.8100000000000005*cos(state[1]);
   out_8819561164250357809[2] = 0;
   out_8819561164250357809[3] = 0;
   out_8819561164250357809[4] = -state[8];
   out_8819561164250357809[5] = state[7];
   out_8819561164250357809[6] = 0;
   out_8819561164250357809[7] = state[5];
   out_8819561164250357809[8] = -state[4];
   out_8819561164250357809[9] = 0;
   out_8819561164250357809[10] = 0;
   out_8819561164250357809[11] = 0;
   out_8819561164250357809[12] = 1;
   out_8819561164250357809[13] = 0;
   out_8819561164250357809[14] = 0;
   out_8819561164250357809[15] = 1;
   out_8819561164250357809[16] = 0;
   out_8819561164250357809[17] = 0;
   out_8819561164250357809[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_8819561164250357809[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_8819561164250357809[20] = 0;
   out_8819561164250357809[21] = state[8];
   out_8819561164250357809[22] = 0;
   out_8819561164250357809[23] = -state[6];
   out_8819561164250357809[24] = -state[5];
   out_8819561164250357809[25] = 0;
   out_8819561164250357809[26] = state[3];
   out_8819561164250357809[27] = 0;
   out_8819561164250357809[28] = 0;
   out_8819561164250357809[29] = 0;
   out_8819561164250357809[30] = 0;
   out_8819561164250357809[31] = 1;
   out_8819561164250357809[32] = 0;
   out_8819561164250357809[33] = 0;
   out_8819561164250357809[34] = 1;
   out_8819561164250357809[35] = 0;
   out_8819561164250357809[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_8819561164250357809[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_8819561164250357809[38] = 0;
   out_8819561164250357809[39] = -state[7];
   out_8819561164250357809[40] = state[6];
   out_8819561164250357809[41] = 0;
   out_8819561164250357809[42] = state[4];
   out_8819561164250357809[43] = -state[3];
   out_8819561164250357809[44] = 0;
   out_8819561164250357809[45] = 0;
   out_8819561164250357809[46] = 0;
   out_8819561164250357809[47] = 0;
   out_8819561164250357809[48] = 0;
   out_8819561164250357809[49] = 0;
   out_8819561164250357809[50] = 1;
   out_8819561164250357809[51] = 0;
   out_8819561164250357809[52] = 0;
   out_8819561164250357809[53] = 1;
}
void h_13(double *state, double *unused, double *out_7498356512665992460) {
   out_7498356512665992460[0] = state[3];
   out_7498356512665992460[1] = state[4];
   out_7498356512665992460[2] = state[5];
}
void H_13(double *state, double *unused, double *out_3727174619203256865) {
   out_3727174619203256865[0] = 0;
   out_3727174619203256865[1] = 0;
   out_3727174619203256865[2] = 0;
   out_3727174619203256865[3] = 1;
   out_3727174619203256865[4] = 0;
   out_3727174619203256865[5] = 0;
   out_3727174619203256865[6] = 0;
   out_3727174619203256865[7] = 0;
   out_3727174619203256865[8] = 0;
   out_3727174619203256865[9] = 0;
   out_3727174619203256865[10] = 0;
   out_3727174619203256865[11] = 0;
   out_3727174619203256865[12] = 0;
   out_3727174619203256865[13] = 0;
   out_3727174619203256865[14] = 0;
   out_3727174619203256865[15] = 0;
   out_3727174619203256865[16] = 0;
   out_3727174619203256865[17] = 0;
   out_3727174619203256865[18] = 0;
   out_3727174619203256865[19] = 0;
   out_3727174619203256865[20] = 0;
   out_3727174619203256865[21] = 0;
   out_3727174619203256865[22] = 1;
   out_3727174619203256865[23] = 0;
   out_3727174619203256865[24] = 0;
   out_3727174619203256865[25] = 0;
   out_3727174619203256865[26] = 0;
   out_3727174619203256865[27] = 0;
   out_3727174619203256865[28] = 0;
   out_3727174619203256865[29] = 0;
   out_3727174619203256865[30] = 0;
   out_3727174619203256865[31] = 0;
   out_3727174619203256865[32] = 0;
   out_3727174619203256865[33] = 0;
   out_3727174619203256865[34] = 0;
   out_3727174619203256865[35] = 0;
   out_3727174619203256865[36] = 0;
   out_3727174619203256865[37] = 0;
   out_3727174619203256865[38] = 0;
   out_3727174619203256865[39] = 0;
   out_3727174619203256865[40] = 0;
   out_3727174619203256865[41] = 1;
   out_3727174619203256865[42] = 0;
   out_3727174619203256865[43] = 0;
   out_3727174619203256865[44] = 0;
   out_3727174619203256865[45] = 0;
   out_3727174619203256865[46] = 0;
   out_3727174619203256865[47] = 0;
   out_3727174619203256865[48] = 0;
   out_3727174619203256865[49] = 0;
   out_3727174619203256865[50] = 0;
   out_3727174619203256865[51] = 0;
   out_3727174619203256865[52] = 0;
   out_3727174619203256865[53] = 0;
}
void h_14(double *state, double *unused, double *out_8629774665379486755) {
   out_8629774665379486755[0] = state[6];
   out_8629774665379486755[1] = state[7];
   out_8629774665379486755[2] = state[8];
}
void H_14(double *state, double *unused, double *out_4478141650210408593) {
   out_4478141650210408593[0] = 0;
   out_4478141650210408593[1] = 0;
   out_4478141650210408593[2] = 0;
   out_4478141650210408593[3] = 0;
   out_4478141650210408593[4] = 0;
   out_4478141650210408593[5] = 0;
   out_4478141650210408593[6] = 1;
   out_4478141650210408593[7] = 0;
   out_4478141650210408593[8] = 0;
   out_4478141650210408593[9] = 0;
   out_4478141650210408593[10] = 0;
   out_4478141650210408593[11] = 0;
   out_4478141650210408593[12] = 0;
   out_4478141650210408593[13] = 0;
   out_4478141650210408593[14] = 0;
   out_4478141650210408593[15] = 0;
   out_4478141650210408593[16] = 0;
   out_4478141650210408593[17] = 0;
   out_4478141650210408593[18] = 0;
   out_4478141650210408593[19] = 0;
   out_4478141650210408593[20] = 0;
   out_4478141650210408593[21] = 0;
   out_4478141650210408593[22] = 0;
   out_4478141650210408593[23] = 0;
   out_4478141650210408593[24] = 0;
   out_4478141650210408593[25] = 1;
   out_4478141650210408593[26] = 0;
   out_4478141650210408593[27] = 0;
   out_4478141650210408593[28] = 0;
   out_4478141650210408593[29] = 0;
   out_4478141650210408593[30] = 0;
   out_4478141650210408593[31] = 0;
   out_4478141650210408593[32] = 0;
   out_4478141650210408593[33] = 0;
   out_4478141650210408593[34] = 0;
   out_4478141650210408593[35] = 0;
   out_4478141650210408593[36] = 0;
   out_4478141650210408593[37] = 0;
   out_4478141650210408593[38] = 0;
   out_4478141650210408593[39] = 0;
   out_4478141650210408593[40] = 0;
   out_4478141650210408593[41] = 0;
   out_4478141650210408593[42] = 0;
   out_4478141650210408593[43] = 0;
   out_4478141650210408593[44] = 1;
   out_4478141650210408593[45] = 0;
   out_4478141650210408593[46] = 0;
   out_4478141650210408593[47] = 0;
   out_4478141650210408593[48] = 0;
   out_4478141650210408593[49] = 0;
   out_4478141650210408593[50] = 0;
   out_4478141650210408593[51] = 0;
   out_4478141650210408593[52] = 0;
   out_4478141650210408593[53] = 0;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_6785328779902013998) {
  err_fun(nom_x, delta_x, out_6785328779902013998);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2829352640446112927) {
  inv_err_fun(nom_x, true_x, out_2829352640446112927);
}
void pose_H_mod_fun(double *state, double *out_8987481613780806210) {
  H_mod_fun(state, out_8987481613780806210);
}
void pose_f_fun(double *state, double dt, double *out_4410802230801501271) {
  f_fun(state,  dt, out_4410802230801501271);
}
void pose_F_fun(double *state, double dt, double *out_2018795142748431206) {
  F_fun(state,  dt, out_2018795142748431206);
}
void pose_h_4(double *state, double *unused, double *out_2992805398127947193) {
  h_4(state, unused, out_2992805398127947193);
}
void pose_H_4(double *state, double *unused, double *out_514900793870924064) {
  H_4(state, unused, out_514900793870924064);
}
void pose_h_10(double *state, double *unused, double *out_1631737084541257867) {
  h_10(state, unused, out_1631737084541257867);
}
void pose_H_10(double *state, double *unused, double *out_8819561164250357809) {
  H_10(state, unused, out_8819561164250357809);
}
void pose_h_13(double *state, double *unused, double *out_7498356512665992460) {
  h_13(state, unused, out_7498356512665992460);
}
void pose_H_13(double *state, double *unused, double *out_3727174619203256865) {
  H_13(state, unused, out_3727174619203256865);
}
void pose_h_14(double *state, double *unused, double *out_8629774665379486755) {
  h_14(state, unused, out_8629774665379486755);
}
void pose_H_14(double *state, double *unused, double *out_4478141650210408593) {
  H_14(state, unused, out_4478141650210408593);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)
