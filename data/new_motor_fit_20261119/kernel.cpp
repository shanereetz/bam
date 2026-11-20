#include <cmath>
#include <algorithm>
extern "C" void rollout(int n,int t,const double *meta,const double *goal,const double *enabled,const double *initial,const double *p,int model,double *out){
// p: kt,R,armature,error_gain_ratio,max_velocity,q_offset,command_delay,friction_base,friction_viscous,friction_stribeck,dtheta_stribeck,alpha,load_friction_base
const double dt=.005;
for(int j=0;j<n;j++){
 const double *m=meta+5*j; double q=initial[2*j],dq=initial[2*j+1],target=q;
 double inertia=(m[0]+m[1]/3)*m[2]*m[2]+p[2];
 for(int k=0;k<t;k++){
  out[j*t+k]=q;
  double d=p[6]/dt;int d0=(int)std::floor(d);double f=d-d0;
  double g=(1-f)*goal[j*t+std::max(0,k-d0)]+f*goal[j*t+std::max(0,k-d0-1)];
  target=std::clamp(g,target-p[4]*dt,target+p[4]*dt);
  double volts=m[4]*std::clamp((target-q)*m[3]*.166*p[3],-.97,.97);
  double mt=(p[0]*volts/p[1]-p[0]*p[0]*dq/p[1])*enabled[j*t+k];
  double bt=-(m[0]+m[1]/2)*9.80665*m[2]*std::sin(q+p[5]);
  double friction=p[7];
  if(model==2)friction+=p[9]*std::exp(-std::pow(std::abs(dq/p[10]),p[11]));
  if(model==3)friction+=p[12]*std::abs(bt-mt);
  double net=mt+bt;double stop=inertia/dt*dq+net;
  net-=((stop>0)-(stop<0))*std::min(std::abs(stop),friction+p[8]*std::abs(dq));
  dq=std::clamp(dq+net/inertia*dt,-100.,100.);q+=dq*dt;
 }
}
}
