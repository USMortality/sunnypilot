#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void live_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_9(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_12(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_35(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_32(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_33(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_H(double *in_vec, double *out_2681185323565379717);
void live_err_fun(double *nom_x, double *delta_x, double *out_4693042988997447555);
void live_inv_err_fun(double *nom_x, double *true_x, double *out_5092507684226011969);
void live_H_mod_fun(double *state, double *out_8624842605842030319);
void live_f_fun(double *state, double dt, double *out_5485499873750470048);
void live_F_fun(double *state, double dt, double *out_4278408746893765928);
void live_h_4(double *state, double *unused, double *out_3085329442796361794);
void live_H_4(double *state, double *unused, double *out_647824108403278587);
void live_h_9(double *state, double *unused, double *out_1926228459984546584);
void live_H_9(double *state, double *unused, double *out_7935043043667726057);
void live_h_10(double *state, double *unused, double *out_2844150599648077085);
void live_H_10(double *state, double *unused, double *out_4705918842076100012);
void live_h_12(double *state, double *unused, double *out_5736335238903855509);
void live_H_12(double *state, double *unused, double *out_1268923133450872254);
void live_h_35(double *state, double *unused, double *out_6187801843038474463);
void live_H_35(double *state, double *unused, double *out_4014486165775885963);
void live_h_32(double *state, double *unused, double *out_1295045048406619867);
void live_H_32(double *state, double *unused, double *out_2369646656064986361);
void live_h_13(double *state, double *unused, double *out_3529164398934071673);
void live_H_13(double *state, double *unused, double *out_1430860474655931643);
void live_h_14(double *state, double *unused, double *out_1926228459984546584);
void live_H_14(double *state, double *unused, double *out_7935043043667726057);
void live_h_33(double *state, double *unused, double *out_5592990643024695797);
void live_H_33(double *state, double *unused, double *out_7165043170414743567);
void live_predict(double *in_x, double *in_P, double *in_Q, double dt);
}