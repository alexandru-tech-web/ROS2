/* hil_firmware_reference.ino — REFERINTA de firmware (Arduino/ESP32) pentru
 * protocolul hw_link: $CMD,v,w*CK -> PWM diferential; raporteaza $POS.
 * NETESTAT pe hardware aici — schelet de pornire, de adaptat la driverul tau
 * (TB6612/L298N) si la encodere. Watchdog PROPRIU de 400 ms (aparare in
 * adancime, pe langa SafetyGate-ul din robot_node). */
const float WHEEL_SEP = 0.42, V_MAX = 1.2;
const int PWM_L = 5, PWM_R = 6, DIR_L = 7, DIR_R = 8;
unsigned long lastCmdMs = 0, lastPosMs = 0; long seq = 0;
float x = 0, y = 0, th = 0, v = 0, w = 0;
String buf;

byte ck(const String& p){ byte c=0; for(unsigned i=0;i<p.length();i++) c^=p[i]; return c; }
void motors(float v,float w){
  float l=v-w*WHEEL_SEP/2, r=v+w*WHEEL_SEP/2;
  digitalWrite(DIR_L,l>=0); digitalWrite(DIR_R,r>=0);
  analogWrite(PWM_L, constrain(abs(l)/V_MAX*255,0,255));
  analogWrite(PWM_R, constrain(abs(r)/V_MAX*255,0,255));
}
void setup(){ Serial.begin(115200);
  pinMode(PWM_L,OUTPUT);pinMode(PWM_R,OUTPUT);
  pinMode(DIR_L,OUTPUT);pinMode(DIR_R,OUTPUT); }
void loop(){
  while(Serial.available()){
    char c=Serial.read();
    if(c=='\n'){
      if(buf.startsWith("$")&&buf.indexOf('*')>0){
        String p=buf.substring(1,buf.lastIndexOf('*'));
        byte want=strtol(buf.substring(buf.lastIndexOf('*')+1).c_str(),0,16);
        if(ck(p)==want&&p.startsWith("CMD,")){
          int c1=p.indexOf(',',4);
          v=p.substring(4,c1).toFloat(); w=p.substring(c1+1).toFloat();
          lastCmdMs=millis();
        }
      }
      buf="";
    } else if(buf.length()<64) buf+=c;
  }
  if(millis()-lastCmdMs>400){ v=0; w=0; }      // watchdog la bord
  motors(v,w);
  unsigned long now=millis();
  if(now-lastPosMs>=50){                        // 20 Hz: dead-reckoning
    float dt=(now-lastPosMs)/1000.0f; lastPosMs=now;
    x+=v*cos(th)*dt; y+=v*sin(th)*dt; th+=w*dt; // de inlocuit cu encodere
    String p="POS,"+String(x,3)+","+String(y,3)+","+String(th,4)+","+String(++seq);
    char s[8]; sprintf(s,"*%02X", ck(p));
    Serial.print("$"); Serial.print(p); Serial.println(s);
  }
}
