#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_7311620110383087435);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5998028402660626913);
void car_H_mod_fun(double *state, double *out_8773945129991319952);
void car_f_fun(double *state, double dt, double *out_8142335827398833520);
void car_F_fun(double *state, double dt, double *out_4091390991401643487);
void car_h_25(double *state, double *unused, double *out_367994228565966054);
void car_H_25(double *state, double *unused, double *out_5250964480001828275);
void car_h_24(double *state, double *unused, double *out_6844014493400491082);
void car_H_24(double *state, double *unused, double *out_8449270266741214307);
void car_h_30(double *state, double *unused, double *out_7513278422188083131);
void car_H_30(double *state, double *unused, double *out_1665725861489788480);
void car_h_26(double *state, double *unused, double *out_6909962537511605614);
void car_H_26(double *state, double *unused, double *out_8992467798875884499);
void car_h_27(double *state, double *unused, double *out_4633679039094879591);
void car_H_27(double *state, double *unused, double *out_7555066738945493256);
void car_h_29(double *state, double *unused, double *out_3129586217725792850);
void car_H_29(double *state, double *unused, double *out_9178314607894507327);
void car_h_28(double *state, double *unused, double *out_3690169186193217156);
void car_H_28(double *state, double *unused, double *out_7304799194249718038);
void car_h_31(double *state, double *unused, double *out_4005443756819988404);
void car_H_31(double *state, double *unused, double *out_5220318518124867847);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}