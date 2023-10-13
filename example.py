#!/usr/bin/env python3
# mypy: ignore-errors
from __future__ import annotations

import time
import binascii

from pypacket import (
  Const,
  Field,
  Child,
  frame,
  calcsize,
  utf8size,
  utf8tobytes,
  utf8frombytes,
  encode,
  decode
)

# the frame decorator is used to specify the structure of the packet, indicating how each field must be serialized
@frame(
  # each object attribute to include in the serialization is specified with its name as the parameter name and a Field object as its value
  # the first argument to Field is the format string (from python's struct module) to be used to encode/decode the attribute
  # the order argument allows to specify the byte order of the field (from python's struct module; default=">" [big-endian])
  # the enc and dec arguments allow to specify a function which will be called before/after the attribute is encoded/decoded
  #   NOTE:
  #     the order of the parameters will determine the order they are serialized
  #     the return type of the enc function must match the type specified in the format string
  #     the return type of the dec function must match the class' attribute type
  x=Field("H", order="<", enc=lambda x: int(x * 100), dec=lambda x: float(x / 100)), # unsigned short little-endian
  y=Field("H", order="@", enc=lambda x: int(x * 100), dec=lambda x: float(x / 100)), # unsigned short with native order
)
# a class is defined with the same parameters passed to the frame decorator as class attributes
class Point:
  x: float
  y: float

# the frame decorator will return the processed class as a dataclass, therefore, an object can be created as follows
p = Point(420.69, 13.37)
print(p) # Point(x=420.69, y=13.37)
# to encode the object the encode() function is used
# a bytearray buffer and offset can be passed through the buffer and offset parameters (in case you need to encode different object to the same buffer)
buff, size = encode(p) # buff: bytearray buffer with encoded object, s: encoded object size
print(binascii.hexlify(buff).decode("utf-8"), size) # 55a43905 4
# to decode the object the decode() function is used with the expected type to decode as the first parameter and the data buffer to decode from as the second
print(*decode(Point, buff), end="\n\n") # Point(x=420.69, y=13.37) 4

# packets can also have variable-sized fields (e.g. strings)
# two different fields are used to specify a variable-sized field, the first indicating the second's size
@frame(
  age=Field("B"),
  height=Field("f"),
  weight=Field("f"),
  # meta=True indicates that this is a metadata field (its value depends on another field)
  name_size=Field("B", meta=True),
  # the name of the field indicating the name size is specified between curly braces in the format string
  name=Field("{name_size}s", enc=utf8tobytes, dec=utf8frombytes)
)
class Person:
  age: int
  height: float
  weight: float
  name: str
  # a property is defined to indicate the current size of the field
  @property
  def name_size(self) -> int: return utf8size(self.name)

p = Person(22, 180.0, 66.75, "Fogell McLovin")
print(p) # Person(age=22, height=180.0, weight=66.75, name='Fogell McLovin')
buff, size = encode(p)
print(binascii.hexlify(buff).decode("utf-8"), size) # 1600003443008085420e466f67656c6c204d634c6f76696e 24
print(*decode(Person, buff), end="\n\n") # Person(age=22, height=180.0, weight=66.75, name='Fogell McLovin') 24

# it is very common to have some packet fields as control fields (e.g. packet header to identify the packet type and/or packet version), this can be done with the Const class
# a Const has the same parameters as Field except for the first one, which indicates its value
# when decoding a Const, if the decoded value does not match the expected value an error will be raised
@frame(
  _id=Const(0x45, "B"), # packet id (identifies the packet type with a unique value)
  _version=Const(0x01, "B"), # packet version (indicates the packet type version)
  unixtime=Field("L")
)
class Time:
  unixtime: int

t = Time(int(time.time()))
print(t) # Time(unixtime=1697915180)
buff, size = encode(t)
print(binascii.hexlify(buff).decode("utf-8"), size) # 45016534212c 6
print(*decode(Time, buff), end="\n\n") # Time(unixtime=1697915180) 6

# the size of bytes of an object can be calculated using the calcsize() function
print(p, calcsize(p)) # Person(age=22, height=180.0, weight=66.75, name='Fogell McLovin') 24
print(t, calcsize(t), end="\n\n") # Time(unixtime=1697964674) 6

# a frame can also have other packet objects as childs, this can be done with the Child class
@frame(
  _id=Const(0xff, "B"),
  # specify the expected object types as positional arguments to Child
  # the count parameter specifies the amount of packet child objects
  # if count=1 then the attribute is treated like an object, instead of a list (note the type annotations on the class' attributes)
  person=Child(Person, count=1),
  register_timestamp=Child(Time, count=1),
  # Child can also a dynamic size/count
  # this can be achieved by creating a separate Field with meta=True and indicating its name in the size/count parameter of Child
  friends_size=Field("H", meta=True),
  friends=Child(Person, size="friends_size"), # size indicates the number of bytes of the whole field (see friends_size property)
  enemies_count=Field("H", meta=True),
  enemies=Child(Person, count="enemies_count") # count indicates the number of objects in the field (see enemies_count property)
)
class Player:
  person: Person
  register_timestamp: Time
  friends: list[Person]
  enemies: list[Person]
  # property indicating the number of bytes in the friends attribute
  @property
  def friends_size(self) -> int: return sum(calcsize(x) for x in self.friends)
  # property indicating the amount of object in the enemies attribute
  @property
  def enemies_count(self) -> int: return len(self.enemies)

p = Player(
  Person(21, 173.0, 59.75, "Jim"),
  Time(int(time.time())),
  [Person(20, 180.0, 65.25, "Michael"), Person(25, 190.75, 80.0, "Pam"), Person(26, 187.0, 89.0, "Darryl")],
  [Person(20, 200.0, 88.0, "Dwight"), Person(19, 188.0, 78.0, "Mose")]
)
print(p)
# Player(
#   person=Person(age=21, height=173.0, weight=59.75, name='Jim'),
#   register_timestamp=Time(unixtime=1697964823),
#   friends=[Person(age=20, height=180.0, weight=65.25, name='Michael'), Person(age=25, height=190.75, weight=80.0, name='Pam'), Person(age=26, height=187.0, weight=89.0, name='Darryl')],
#   enemies=[Person(age=20, height=200.0, weight=88.0, name='Dwight'), Person(age=19, height=188.0, weight=78.0, name='Mose')])
buff, size = encode(p)
print(binascii.hexlify(buff).decode("utf-8"), size)
# ff15432d0000426f0000034a696d45016534e317002e144334000042828000074d69636861656c19433ec00042a000000350616d1a433b000042b200000644617272796c0002144348000042b000000644776967687413433c0000429c0000044d6f7365 100
print(*decode(Player, buff), end="\n\n")
# Player(
#   person=Person(age=21, height=173.0, weight=59.75, name='Jim'),
#   register_timestamp=Time(unixtime=1697964823),
#   friends=[Person(age=20, height=180.0, weight=65.25, name='Michael'), Person(age=25, height=190.75, weight=80.0, name='Pam'), Person(age=26, height=187.0, weight=89.0, name='Darryl')],
#   enemies=[Person(age=20, height=200.0, weight=88.0, name='Dwight'), Person(age=19, height=188.0, weight=78.0, name='Mose')]) 100

# if a Child does not have a size or count it will be encoded/decoded until the end of the object list/byte stream
@frame(
  points=Child(Point)
)
class PointList:
  points: list[Point]

p = PointList([Point(10.25, 125.0)] * 5)
print(p) # PointList(points=[Point(x=10.25, y=125.0), Point(x=10.25, y=125.0), Point(x=10.25, y=125.0), Point(x=10.25, y=125.0), Point(x=10.25, y=125.0)])
buff, size = encode(p)
print(binascii.hexlify(buff).decode("utf-8"), size) # 0104d4300104d4300104d4300104d4300104d430 20
print(*decode(PointList, buff), end="\n\n") # PointList(points=[Point(x=10.25, y=125.0), Point(x=10.25, y=125.0), Point(x=10.25, y=125.0), Point(x=10.25, y=125.0), Point(x=10.25, y=125.0)]) 20

# a Child can also have arbitrarily many packet subtypes with any order (only if each packet subtype has some Const identifying it)
@frame(
  objects=Child(Time, Player)
)
class Dummy:
  objects: list[Time | Player]

d = Dummy([
    Time(int(time.time())),
    Player(
      Person(21, 173.0, 59.75, "Jim"),
      Time(int(time.time())),
      [Person(20, 180.0, 65.25, "Michael"), Person(25, 190.75, 80.0, "Pam"), Person(26, 187.0, 89.0, "Darryl")],
      [Person(20, 200.0, 88.0, "Dwight"), Person(19, 188.0, 78.0, "Mose")]
    ),
    Time(int(time.time()))
  ]
)
print(d)
# Dummy(objects=[
#   Time(unixtime=1697966449),
#   Player(person=Person(age=21, height=173.0, weight=59.75, name='Jim'), register_timestamp=Time(unixtime=1697966449), friends=[Person(age=20, height=180.0, weight=65.25, name='Michael'), Person(age=25, height=190.75, weight=80.0, name='Pam'), Person(age=26, height=187.0, weight=89.0, name='Darryl')], enemies=[Person(age=20, height=200.0, weight=88.0, name='Dwight'), Person(age=19, height=188.0, weight=78.0, name='Mose')]),
#   Time(unixtime=1697966449)])
buff, size = encode(d)
print(binascii.hexlify(buff).decode("utf-8"), size)
# 45016534e971ff15432d0000426f0000034a696d45016534e971002e144334000042828000074d69636861656c19433ec00042a000000350616d1a433b000042b200000644617272796c0002144348000042b000000644776967687413433c0000429c0000044d6f736545016534e971 112
print(*decode(Dummy, buff), end="\n\n")
# Dummy(objects=[
#   Time(unixtime=1697966449),
#   Player(person=Person(age=21, height=173.0, weight=59.75, name='Jim'), register_timestamp=Time(unixtime=1697966449), friends=[Person(age=20, height=180.0, weight=65.25, name='Michael'), Person(age=25, height=190.75, weight=80.0, name='Pam'), Person(age=26, height=187.0, weight=89.0, name='Darryl')], enemies=[Person(age=20, height=200.0, weight=88.0, name='Dwight'), Person(age=19, height=188.0, weight=78.0, name='Mose')]),
#   Time(unixtime=1697966449)]) 112

def bytestoint8(val: bytes) -> list[int]: return [x if isinstance(x, int) else int.from_bytes(x) for x in val]
def int8tobytes(val: list[int]) -> bytes: return val.to_bytes(1)

@frame(value=Field("B", stop="\x00", enc=(utf8tobytes, bytestoint8), dec=(int8tobytes, utf8frombytes)))
class String:
  value: str

  def __init__(self, value: str | list[str]):
    if isinstance(value, list): value = "".join(value)
    self.value = value

s = String("this is a stop test, is it working?")
print(s)
buff, size = encode(s)
print(binascii.hexlify(buff).decode("utf-8"), size)
print(*decode(String, buff), end="\n\n")