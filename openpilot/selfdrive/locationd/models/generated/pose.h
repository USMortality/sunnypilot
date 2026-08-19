#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_6785328779902013998);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2829352640446112927);
void pose_H_mod_fun(double *state, double *out_8987481613780806210);
void pose_f_fun(double *state, double dt, double *out_4410802230801501271);
void pose_F_fun(double *state, double dt, double *out_2018795142748431206);
void pose_h_4(double *state, double *unused, double *out_2992805398127947193);
void pose_H_4(double *state, double *unused, double *out_514900793870924064);
void pose_h_10(double *state, double *unused, double *out_1631737084541257867);
void pose_H_10(double *state, double *unused, double *out_8819561164250357809);
void pose_h_13(double *state, double *unused, double *out_7498356512665992460);
void pose_H_13(double *state, double *unused, double *out_3727174619203256865);
void pose_h_14(double *state, double *unused, double *out_8629774665379486755);
void pose_H_14(double *state, double *unused, double *out_4478141650210408593);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}