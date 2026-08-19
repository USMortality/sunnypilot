#include "car.h"

namespace {
#define DIM 9
#define EDIM 9
#define MEDIM 9
typedef void (*Hfun)(double *, double *, double *);

double mass;

void set_mass(double x){ mass = x;}

double rotational_inertia;

void set_rotational_inertia(double x){ rotational_inertia = x;}

double center_to_front;

void set_center_to_front(double x){ center_to_front = x;}

double center_to_rear;

void set_center_to_rear(double x){ center_to_rear = x;}

double stiffness_front;

void set_stiffness_front(double x){ stiffness_front = x;}

double stiffness_rear;

void set_stiffness_rear(double x){ stiffness_rear = x;}
const static double MAHA_THRESH_25 = 3.8414588206941227;
const static double MAHA_THRESH_24 = 5.991464547107981;
const static double MAHA_THRESH_30 = 3.8414588206941227;
const static double MAHA_THRESH_26 = 3.8414588206941227;
const static double MAHA_THRESH_27 = 3.8414588206941227;
const static double MAHA_THRESH_29 = 3.8414588206941227;
const static double MAHA_THRESH_28 = 3.8414588206941227;
const static double MAHA_THRESH_31 = 3.8414588206941227;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_7311620110383087435) {
   out_7311620110383087435[0] = delta_x[0] + nom_x[0];
   out_7311620110383087435[1] = delta_x[1] + nom_x[1];
   out_7311620110383087435[2] = delta_x[2] + nom_x[2];
   out_7311620110383087435[3] = delta_x[3] + nom_x[3];
   out_7311620110383087435[4] = delta_x[4] + nom_x[4];
   out_7311620110383087435[5] = delta_x[5] + nom_x[5];
   out_7311620110383087435[6] = delta_x[6] + nom_x[6];
   out_7311620110383087435[7] = delta_x[7] + nom_x[7];
   out_7311620110383087435[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_5998028402660626913) {
   out_5998028402660626913[0] = -nom_x[0] + true_x[0];
   out_5998028402660626913[1] = -nom_x[1] + true_x[1];
   out_5998028402660626913[2] = -nom_x[2] + true_x[2];
   out_5998028402660626913[3] = -nom_x[3] + true_x[3];
   out_5998028402660626913[4] = -nom_x[4] + true_x[4];
   out_5998028402660626913[5] = -nom_x[5] + true_x[5];
   out_5998028402660626913[6] = -nom_x[6] + true_x[6];
   out_5998028402660626913[7] = -nom_x[7] + true_x[7];
   out_5998028402660626913[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_8773945129991319952) {
   out_8773945129991319952[0] = 1.0;
   out_8773945129991319952[1] = 0.0;
   out_8773945129991319952[2] = 0.0;
   out_8773945129991319952[3] = 0.0;
   out_8773945129991319952[4] = 0.0;
   out_8773945129991319952[5] = 0.0;
   out_8773945129991319952[6] = 0.0;
   out_8773945129991319952[7] = 0.0;
   out_8773945129991319952[8] = 0.0;
   out_8773945129991319952[9] = 0.0;
   out_8773945129991319952[10] = 1.0;
   out_8773945129991319952[11] = 0.0;
   out_8773945129991319952[12] = 0.0;
   out_8773945129991319952[13] = 0.0;
   out_8773945129991319952[14] = 0.0;
   out_8773945129991319952[15] = 0.0;
   out_8773945129991319952[16] = 0.0;
   out_8773945129991319952[17] = 0.0;
   out_8773945129991319952[18] = 0.0;
   out_8773945129991319952[19] = 0.0;
   out_8773945129991319952[20] = 1.0;
   out_8773945129991319952[21] = 0.0;
   out_8773945129991319952[22] = 0.0;
   out_8773945129991319952[23] = 0.0;
   out_8773945129991319952[24] = 0.0;
   out_8773945129991319952[25] = 0.0;
   out_8773945129991319952[26] = 0.0;
   out_8773945129991319952[27] = 0.0;
   out_8773945129991319952[28] = 0.0;
   out_8773945129991319952[29] = 0.0;
   out_8773945129991319952[30] = 1.0;
   out_8773945129991319952[31] = 0.0;
   out_8773945129991319952[32] = 0.0;
   out_8773945129991319952[33] = 0.0;
   out_8773945129991319952[34] = 0.0;
   out_8773945129991319952[35] = 0.0;
   out_8773945129991319952[36] = 0.0;
   out_8773945129991319952[37] = 0.0;
   out_8773945129991319952[38] = 0.0;
   out_8773945129991319952[39] = 0.0;
   out_8773945129991319952[40] = 1.0;
   out_8773945129991319952[41] = 0.0;
   out_8773945129991319952[42] = 0.0;
   out_8773945129991319952[43] = 0.0;
   out_8773945129991319952[44] = 0.0;
   out_8773945129991319952[45] = 0.0;
   out_8773945129991319952[46] = 0.0;
   out_8773945129991319952[47] = 0.0;
   out_8773945129991319952[48] = 0.0;
   out_8773945129991319952[49] = 0.0;
   out_8773945129991319952[50] = 1.0;
   out_8773945129991319952[51] = 0.0;
   out_8773945129991319952[52] = 0.0;
   out_8773945129991319952[53] = 0.0;
   out_8773945129991319952[54] = 0.0;
   out_8773945129991319952[55] = 0.0;
   out_8773945129991319952[56] = 0.0;
   out_8773945129991319952[57] = 0.0;
   out_8773945129991319952[58] = 0.0;
   out_8773945129991319952[59] = 0.0;
   out_8773945129991319952[60] = 1.0;
   out_8773945129991319952[61] = 0.0;
   out_8773945129991319952[62] = 0.0;
   out_8773945129991319952[63] = 0.0;
   out_8773945129991319952[64] = 0.0;
   out_8773945129991319952[65] = 0.0;
   out_8773945129991319952[66] = 0.0;
   out_8773945129991319952[67] = 0.0;
   out_8773945129991319952[68] = 0.0;
   out_8773945129991319952[69] = 0.0;
   out_8773945129991319952[70] = 1.0;
   out_8773945129991319952[71] = 0.0;
   out_8773945129991319952[72] = 0.0;
   out_8773945129991319952[73] = 0.0;
   out_8773945129991319952[74] = 0.0;
   out_8773945129991319952[75] = 0.0;
   out_8773945129991319952[76] = 0.0;
   out_8773945129991319952[77] = 0.0;
   out_8773945129991319952[78] = 0.0;
   out_8773945129991319952[79] = 0.0;
   out_8773945129991319952[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_8142335827398833520) {
   out_8142335827398833520[0] = state[0];
   out_8142335827398833520[1] = state[1];
   out_8142335827398833520[2] = state[2];
   out_8142335827398833520[3] = state[3];
   out_8142335827398833520[4] = state[4];
   out_8142335827398833520[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_8142335827398833520[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_8142335827398833520[7] = state[7];
   out_8142335827398833520[8] = state[8];
}
void F_fun(double *state, double dt, double *out_4091390991401643487) {
   out_4091390991401643487[0] = 1;
   out_4091390991401643487[1] = 0;
   out_4091390991401643487[2] = 0;
   out_4091390991401643487[3] = 0;
   out_4091390991401643487[4] = 0;
   out_4091390991401643487[5] = 0;
   out_4091390991401643487[6] = 0;
   out_4091390991401643487[7] = 0;
   out_4091390991401643487[8] = 0;
   out_4091390991401643487[9] = 0;
   out_4091390991401643487[10] = 1;
   out_4091390991401643487[11] = 0;
   out_4091390991401643487[12] = 0;
   out_4091390991401643487[13] = 0;
   out_4091390991401643487[14] = 0;
   out_4091390991401643487[15] = 0;
   out_4091390991401643487[16] = 0;
   out_4091390991401643487[17] = 0;
   out_4091390991401643487[18] = 0;
   out_4091390991401643487[19] = 0;
   out_4091390991401643487[20] = 1;
   out_4091390991401643487[21] = 0;
   out_4091390991401643487[22] = 0;
   out_4091390991401643487[23] = 0;
   out_4091390991401643487[24] = 0;
   out_4091390991401643487[25] = 0;
   out_4091390991401643487[26] = 0;
   out_4091390991401643487[27] = 0;
   out_4091390991401643487[28] = 0;
   out_4091390991401643487[29] = 0;
   out_4091390991401643487[30] = 1;
   out_4091390991401643487[31] = 0;
   out_4091390991401643487[32] = 0;
   out_4091390991401643487[33] = 0;
   out_4091390991401643487[34] = 0;
   out_4091390991401643487[35] = 0;
   out_4091390991401643487[36] = 0;
   out_4091390991401643487[37] = 0;
   out_4091390991401643487[38] = 0;
   out_4091390991401643487[39] = 0;
   out_4091390991401643487[40] = 1;
   out_4091390991401643487[41] = 0;
   out_4091390991401643487[42] = 0;
   out_4091390991401643487[43] = 0;
   out_4091390991401643487[44] = 0;
   out_4091390991401643487[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_4091390991401643487[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_4091390991401643487[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4091390991401643487[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4091390991401643487[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_4091390991401643487[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_4091390991401643487[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_4091390991401643487[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_4091390991401643487[53] = -9.8100000000000005*dt;
   out_4091390991401643487[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_4091390991401643487[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_4091390991401643487[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4091390991401643487[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4091390991401643487[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_4091390991401643487[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_4091390991401643487[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_4091390991401643487[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4091390991401643487[62] = 0;
   out_4091390991401643487[63] = 0;
   out_4091390991401643487[64] = 0;
   out_4091390991401643487[65] = 0;
   out_4091390991401643487[66] = 0;
   out_4091390991401643487[67] = 0;
   out_4091390991401643487[68] = 0;
   out_4091390991401643487[69] = 0;
   out_4091390991401643487[70] = 1;
   out_4091390991401643487[71] = 0;
   out_4091390991401643487[72] = 0;
   out_4091390991401643487[73] = 0;
   out_4091390991401643487[74] = 0;
   out_4091390991401643487[75] = 0;
   out_4091390991401643487[76] = 0;
   out_4091390991401643487[77] = 0;
   out_4091390991401643487[78] = 0;
   out_4091390991401643487[79] = 0;
   out_4091390991401643487[80] = 1;
}
void h_25(double *state, double *unused, double *out_367994228565966054) {
   out_367994228565966054[0] = state[6];
}
void H_25(double *state, double *unused, double *out_5250964480001828275) {
   out_5250964480001828275[0] = 0;
   out_5250964480001828275[1] = 0;
   out_5250964480001828275[2] = 0;
   out_5250964480001828275[3] = 0;
   out_5250964480001828275[4] = 0;
   out_5250964480001828275[5] = 0;
   out_5250964480001828275[6] = 1;
   out_5250964480001828275[7] = 0;
   out_5250964480001828275[8] = 0;
}
void h_24(double *state, double *unused, double *out_6844014493400491082) {
   out_6844014493400491082[0] = state[4];
   out_6844014493400491082[1] = state[5];
}
void H_24(double *state, double *unused, double *out_8449270266741214307) {
   out_8449270266741214307[0] = 0;
   out_8449270266741214307[1] = 0;
   out_8449270266741214307[2] = 0;
   out_8449270266741214307[3] = 0;
   out_8449270266741214307[4] = 1;
   out_8449270266741214307[5] = 0;
   out_8449270266741214307[6] = 0;
   out_8449270266741214307[7] = 0;
   out_8449270266741214307[8] = 0;
   out_8449270266741214307[9] = 0;
   out_8449270266741214307[10] = 0;
   out_8449270266741214307[11] = 0;
   out_8449270266741214307[12] = 0;
   out_8449270266741214307[13] = 0;
   out_8449270266741214307[14] = 1;
   out_8449270266741214307[15] = 0;
   out_8449270266741214307[16] = 0;
   out_8449270266741214307[17] = 0;
}
void h_30(double *state, double *unused, double *out_7513278422188083131) {
   out_7513278422188083131[0] = state[4];
}
void H_30(double *state, double *unused, double *out_1665725861489788480) {
   out_1665725861489788480[0] = 0;
   out_1665725861489788480[1] = 0;
   out_1665725861489788480[2] = 0;
   out_1665725861489788480[3] = 0;
   out_1665725861489788480[4] = 1;
   out_1665725861489788480[5] = 0;
   out_1665725861489788480[6] = 0;
   out_1665725861489788480[7] = 0;
   out_1665725861489788480[8] = 0;
}
void h_26(double *state, double *unused, double *out_6909962537511605614) {
   out_6909962537511605614[0] = state[7];
}
void H_26(double *state, double *unused, double *out_8992467798875884499) {
   out_8992467798875884499[0] = 0;
   out_8992467798875884499[1] = 0;
   out_8992467798875884499[2] = 0;
   out_8992467798875884499[3] = 0;
   out_8992467798875884499[4] = 0;
   out_8992467798875884499[5] = 0;
   out_8992467798875884499[6] = 0;
   out_8992467798875884499[7] = 1;
   out_8992467798875884499[8] = 0;
}
void h_27(double *state, double *unused, double *out_4633679039094879591) {
   out_4633679039094879591[0] = state[3];
}
void H_27(double *state, double *unused, double *out_7555066738945493256) {
   out_7555066738945493256[0] = 0;
   out_7555066738945493256[1] = 0;
   out_7555066738945493256[2] = 0;
   out_7555066738945493256[3] = 1;
   out_7555066738945493256[4] = 0;
   out_7555066738945493256[5] = 0;
   out_7555066738945493256[6] = 0;
   out_7555066738945493256[7] = 0;
   out_7555066738945493256[8] = 0;
}
void h_29(double *state, double *unused, double *out_3129586217725792850) {
   out_3129586217725792850[0] = state[1];
}
void H_29(double *state, double *unused, double *out_9178314607894507327) {
   out_9178314607894507327[0] = 0;
   out_9178314607894507327[1] = 1;
   out_9178314607894507327[2] = 0;
   out_9178314607894507327[3] = 0;
   out_9178314607894507327[4] = 0;
   out_9178314607894507327[5] = 0;
   out_9178314607894507327[6] = 0;
   out_9178314607894507327[7] = 0;
   out_9178314607894507327[8] = 0;
}
void h_28(double *state, double *unused, double *out_3690169186193217156) {
   out_3690169186193217156[0] = state[0];
}
void H_28(double *state, double *unused, double *out_7304799194249718038) {
   out_7304799194249718038[0] = 1;
   out_7304799194249718038[1] = 0;
   out_7304799194249718038[2] = 0;
   out_7304799194249718038[3] = 0;
   out_7304799194249718038[4] = 0;
   out_7304799194249718038[5] = 0;
   out_7304799194249718038[6] = 0;
   out_7304799194249718038[7] = 0;
   out_7304799194249718038[8] = 0;
}
void h_31(double *state, double *unused, double *out_4005443756819988404) {
   out_4005443756819988404[0] = state[8];
}
void H_31(double *state, double *unused, double *out_5220318518124867847) {
   out_5220318518124867847[0] = 0;
   out_5220318518124867847[1] = 0;
   out_5220318518124867847[2] = 0;
   out_5220318518124867847[3] = 0;
   out_5220318518124867847[4] = 0;
   out_5220318518124867847[5] = 0;
   out_5220318518124867847[6] = 0;
   out_5220318518124867847[7] = 0;
   out_5220318518124867847[8] = 1;
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

void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_25, H_25, NULL, in_z, in_R, in_ea, MAHA_THRESH_25);
}
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<2, 3, 0>(in_x, in_P, h_24, H_24, NULL, in_z, in_R, in_ea, MAHA_THRESH_24);
}
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_30, H_30, NULL, in_z, in_R, in_ea, MAHA_THRESH_30);
}
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_26, H_26, NULL, in_z, in_R, in_ea, MAHA_THRESH_26);
}
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_27, H_27, NULL, in_z, in_R, in_ea, MAHA_THRESH_27);
}
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_29, H_29, NULL, in_z, in_R, in_ea, MAHA_THRESH_29);
}
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_28, H_28, NULL, in_z, in_R, in_ea, MAHA_THRESH_28);
}
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_31, H_31, NULL, in_z, in_R, in_ea, MAHA_THRESH_31);
}
void car_err_fun(double *nom_x, double *delta_x, double *out_7311620110383087435) {
  err_fun(nom_x, delta_x, out_7311620110383087435);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5998028402660626913) {
  inv_err_fun(nom_x, true_x, out_5998028402660626913);
}
void car_H_mod_fun(double *state, double *out_8773945129991319952) {
  H_mod_fun(state, out_8773945129991319952);
}
void car_f_fun(double *state, double dt, double *out_8142335827398833520) {
  f_fun(state,  dt, out_8142335827398833520);
}
void car_F_fun(double *state, double dt, double *out_4091390991401643487) {
  F_fun(state,  dt, out_4091390991401643487);
}
void car_h_25(double *state, double *unused, double *out_367994228565966054) {
  h_25(state, unused, out_367994228565966054);
}
void car_H_25(double *state, double *unused, double *out_5250964480001828275) {
  H_25(state, unused, out_5250964480001828275);
}
void car_h_24(double *state, double *unused, double *out_6844014493400491082) {
  h_24(state, unused, out_6844014493400491082);
}
void car_H_24(double *state, double *unused, double *out_8449270266741214307) {
  H_24(state, unused, out_8449270266741214307);
}
void car_h_30(double *state, double *unused, double *out_7513278422188083131) {
  h_30(state, unused, out_7513278422188083131);
}
void car_H_30(double *state, double *unused, double *out_1665725861489788480) {
  H_30(state, unused, out_1665725861489788480);
}
void car_h_26(double *state, double *unused, double *out_6909962537511605614) {
  h_26(state, unused, out_6909962537511605614);
}
void car_H_26(double *state, double *unused, double *out_8992467798875884499) {
  H_26(state, unused, out_8992467798875884499);
}
void car_h_27(double *state, double *unused, double *out_4633679039094879591) {
  h_27(state, unused, out_4633679039094879591);
}
void car_H_27(double *state, double *unused, double *out_7555066738945493256) {
  H_27(state, unused, out_7555066738945493256);
}
void car_h_29(double *state, double *unused, double *out_3129586217725792850) {
  h_29(state, unused, out_3129586217725792850);
}
void car_H_29(double *state, double *unused, double *out_9178314607894507327) {
  H_29(state, unused, out_9178314607894507327);
}
void car_h_28(double *state, double *unused, double *out_3690169186193217156) {
  h_28(state, unused, out_3690169186193217156);
}
void car_H_28(double *state, double *unused, double *out_7304799194249718038) {
  H_28(state, unused, out_7304799194249718038);
}
void car_h_31(double *state, double *unused, double *out_4005443756819988404) {
  h_31(state, unused, out_4005443756819988404);
}
void car_H_31(double *state, double *unused, double *out_5220318518124867847) {
  H_31(state, unused, out_5220318518124867847);
}
void car_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
void car_set_mass(double x) {
  set_mass(x);
}
void car_set_rotational_inertia(double x) {
  set_rotational_inertia(x);
}
void car_set_center_to_front(double x) {
  set_center_to_front(x);
}
void car_set_center_to_rear(double x) {
  set_center_to_rear(x);
}
void car_set_stiffness_front(double x) {
  set_stiffness_front(x);
}
void car_set_stiffness_rear(double x) {
  set_stiffness_rear(x);
}
}

const EKF car = {
  .name = "car",
  .kinds = { 25, 24, 30, 26, 27, 29, 28, 31 },
  .feature_kinds = {  },
  .f_fun = car_f_fun,
  .F_fun = car_F_fun,
  .err_fun = car_err_fun,
  .inv_err_fun = car_inv_err_fun,
  .H_mod_fun = car_H_mod_fun,
  .predict = car_predict,
  .hs = {
    { 25, car_h_25 },
    { 24, car_h_24 },
    { 30, car_h_30 },
    { 26, car_h_26 },
    { 27, car_h_27 },
    { 29, car_h_29 },
    { 28, car_h_28 },
    { 31, car_h_31 },
  },
  .Hs = {
    { 25, car_H_25 },
    { 24, car_H_24 },
    { 30, car_H_30 },
    { 26, car_H_26 },
    { 27, car_H_27 },
    { 29, car_H_29 },
    { 28, car_H_28 },
    { 31, car_H_31 },
  },
  .updates = {
    { 25, car_update_25 },
    { 24, car_update_24 },
    { 30, car_update_30 },
    { 26, car_update_26 },
    { 27, car_update_27 },
    { 29, car_update_29 },
    { 28, car_update_28 },
    { 31, car_update_31 },
  },
  .Hes = {
  },
  .sets = {
    { "mass", car_set_mass },
    { "rotational_inertia", car_set_rotational_inertia },
    { "center_to_front", car_set_center_to_front },
    { "center_to_rear", car_set_center_to_rear },
    { "stiffness_front", car_set_stiffness_front },
    { "stiffness_rear", car_set_stiffness_rear },
  },
  .extra_routines = {
  },
};

ekf_lib_init(car)
