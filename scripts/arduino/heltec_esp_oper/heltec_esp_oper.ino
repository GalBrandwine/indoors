
#include "heltec.h"
#include <CRC32.h>

// General definitions
#define MAX_PAYLOAD_LEN 256                 // Bytes
#define MAX_MSG_LEN (MAX_PAYLOAD_LEN + 28)	// 28 is the header size
#define SYNC_TIMEOUT 5                      // Seconds

// LoRa -> Host
#define MSG_OPCODE_DEBUG 0x10
#define MSG_OPCODE_DATA 0x20

#define MSG_OK                ((unsigned char *)"OK")
#define MSG_SYNC_ERR          ((unsigned char *)"Sync Error")
#define MSG_HDR_ERR           ((unsigned char *)"HDR Error")
#define MSG_PAYLOAD_ERR       ((unsigned char *)"Payload error")
#define MSG_SYNC_TIMEOUT_ERR  ((unsigned char *)"Sync timeout")
#define MSG_GBG_ERR           ((unsigned char *)"RSV timeout")


// HOST -> LoRa
#define OPCODE_PING 0x10
#define OPCODE_SEND 0x20

// 
#define BAND 868E6  //you can set band here directly,e.g. 433e6,868E6,915E6

void display(char *str, int dis_delay=0)
{
  Heltec.display->clear();
  Heltec.display->drawString(0, 0, str);
  Heltec.display->display();
  delay(dis_delay);

}

void display(int num, int dis_delay=0)
{
  char str[16];

  sprintf(str,"%d", num);
  Heltec.display->clear();
  Heltec.display->drawString(0, 0, str);
  Heltec.display->display();
  delay(dis_delay);

}


void setup() {
  //WIFI Kit series V1 not support Vext control
  Heltec.begin(	true /*DisplayEnable Enable*/, 
		true /*Heltec.Heltec.Heltec.LoRa Disable*/, 
		true /*Serial Enable*/, 
		true /*PABOOST Enable*/, 
		BAND /*long BAND*/);
  // Set Spreading Factor
  Heltec.LoRa.setSpreadingFactor(7); // ranges from 6-12,default 7 see API docs
  Heltec.display->init();
  Heltec.display->flipScreenVertically();  
  Heltec.display->setFont(ArialMT_Plain_10);
  //logo();
  //delay(1500);
  Heltec.display->clear();
  Heltec.display->drawString(0, 0, "Heltec.LoRa Initial success!");
  Heltec.display->display();
  delay(1000);
  LoRa.receive();
}


unsigned long current_time()
{
  return millis() / 1000;   // seconds
}

void send_host(unsigned long opcode, unsigned char *msg, unsigned long length)
{
  unsigned long msg_size;
  unsigned char msg_bin[MAX_MSG_LEN];
  msg_prepare(opcode, 0, 0, msg, length, msg_bin, &msg_size);

  Serial.write(msg_bin, msg_size);
  Serial.flush();
}

unsigned char uard_read_byte()
{
  while (!Serial.available())
  {
    // Wait for incoming byte
  }
  return Serial.read();
}

unsigned long calc_crc32(unsigned char *buff, int size)
{
  CRC32 crc;

  for (int i = 0; i < size; i++)
  {
      crc.update(buff[i]);
  }

  return crc.finalize(); 
}

void msg_prepare(	
	unsigned long opcode, 
	unsigned long param1, 
	unsigned long param2, 
	unsigned char *payload, 
	unsigned long payload_size, 
	unsigned char *msg,
	unsigned long *msg_size)
{
	*msg_size = 28 +payload_size;
  unsigned long *msg_p_32 = (unsigned long *)msg;

	msg_p_32[0]=0xA5A5A5A5;
	msg_p_32[1] = opcode;
	msg_p_32[2] = param1;
	msg_p_32[3] = param2;
	msg_p_32[4] = payload_size;
	if (payload_size)
	{
		msg_p_32[5] = calc_crc32(payload, payload_size);
    unsigned char *p =  (unsigned char *)&msg_p_32[7];
    int i;
    for (i=0; i<payload_size; i++, p++)
    {
      *p = payload[i];
    } 
	}
	else
	{
		msg_p_32[5] = 0;
	}
	msg_p_32[6] = calc_crc32((unsigned char*)msg, 24);
}


int check_sync()
{
  for (int i=0; i<4; i++)
  {
    if (uard_read_byte() != 0xA5)
    {
      return 0;
    }
  }
  return 1;
}

int resync(void)
{
  int cnt = 0;
  unsigned long start_time = current_time();

  while (current_time() - start_time < SYNC_TIMEOUT)
  {
    char val = uard_read_byte();
    if (val == 0xA5)
    {
      cnt++;
    }
    else
    {
      cnt = 0;
    }
    if (cnt == 4)
    {
      return 1;
    }
  }
  return 0;
}


int read_header(unsigned long *opcode, 
    unsigned long *param1, 
    unsigned long *param2, 
    unsigned long *payload_len, 
    unsigned long *payload_crc)
{
  unsigned long header[8];// header include the CRC
  unsigned char *header_p = (unsigned char *)&header[1];// start after the sync word

  header[0] = 0xA5A5A5A5; // Sync word already read but need to participate in the CRC party

  for (int i=0; i<24; i++)
  {
    *header_p = uard_read_byte();
    header_p++;
  }
 
  if (header[6] != calc_crc32((unsigned char *)header, 24))
  {
    return 0;
  }

  *opcode       = header[1];
  *param1       = header[2];
  *param2       = header[3];
  *payload_len  = header[4];
  *payload_crc  = header[5];

  return 1;
} 

int read_payload(unsigned long payload_len, unsigned long payload_crc, unsigned char *payload)
{
  for (int i=0; i<payload_len; i++)
  {
    payload[i] = uard_read_byte();
  }
  if (payload_crc != calc_crc32(payload, payload_len))
  {
    return 0;
  }
  return 1;
}

void host_read()
{
  unsigned long opcode, param1, param2, payload_len, payload_crc;
  int valid;
  unsigned char payload[MAX_PAYLOAD_LEN];
  if (!check_sync())
  {
    send_host(MSG_OPCODE_DEBUG, MSG_SYNC_ERR, strlen((const char*)MSG_SYNC_ERR));
    valid = resync(); // look for sync word
    if (!valid)
    {
      send_host(MSG_OPCODE_DEBUG, MSG_SYNC_TIMEOUT_ERR, strlen((const char*)MSG_SYNC_TIMEOUT_ERR));
      return;
    }
  }

  valid = read_header(&opcode, &param1, &param2, &payload_len, &payload_crc);

  if (!valid)
  {
    send_host(MSG_OPCODE_DEBUG, MSG_HDR_ERR, strlen((const char*)MSG_HDR_ERR));
    return;
  }

  if (payload_len)
  {
    valid = read_payload(payload_len, payload_crc, payload);
    if (!valid)
    {
      send_host(MSG_OPCODE_DEBUG, MSG_PAYLOAD_ERR, strlen((const char*)MSG_PAYLOAD_ERR));
      return;
    }
  }

 switch (opcode)
  {
 
    case OPCODE_PING:
      break;
    case OPCODE_SEND:
      LoRa.beginPacket();
      LoRa.write(payload, payload_len);
      LoRa.endPacket();
      break;
  }
  send_host(MSG_OPCODE_DEBUG, MSG_OK, strlen((const char*)MSG_OK));
}



void loop() {
    static int packet_counter = 0;
    int packetSize;
    if (Serial.available())
    {
      host_read();
    }
    packetSize = LoRa.parsePacket();
    unsigned char buff[MAX_PAYLOAD_LEN];
    int i;
    if (packetSize) 
    {
      for( i=0;i<packetSize; i++) 
      {
        buff[i] = LoRa.read();
      }
      send_host(MSG_OPCODE_DATA, buff, i);
    }
   display(packet_counter);
   packet_counter = 1-packet_counter;
   
    
}
