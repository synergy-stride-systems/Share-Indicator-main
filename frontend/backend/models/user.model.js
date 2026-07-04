import { EntitySchema } from "typeorm";

export const User = new EntitySchema({
  name: "User",
  tableName: "users",

  columns: {
    user_id: {
      type: "uuid",
      primary: true,
      generated: "uuid",
    },

    full_name: {
      type: "varchar",
      length: 100,
    },

    email: {
      type: "varchar",
      length: 100,
      unique: true,
    },

    password: {
      type: "varchar",
      length: 255,
    },


    },
});