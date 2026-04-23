//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1, t = !1;
function n() {
	t = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
n();
//#endregion
//#region node_modules/svelte/src/constants.js
var r = {}, i = Symbol(), a = "http://www.w3.org/1999/xhtml", o = Array.isArray, s = Array.prototype.indexOf, c = Array.prototype.includes, l = Array.from, u = Object.keys, d = Object.defineProperty, f = Object.getOwnPropertyDescriptor, p = Object.getOwnPropertyDescriptors, m = Object.prototype, h = Array.prototype, g = Object.getPrototypeOf, ee = Object.isExtensible, _ = () => {};
function te(e) {
	return e();
}
function ne(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function re() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var v = 1024, y = 2048, b = 4096, ie = 8192, ae = 16384, oe = 32768, se = 1 << 25, ce = 65536, x = 1 << 19, le = 1 << 20, ue = 65536, de = 1 << 21, fe = 1 << 22, pe = 1 << 23, me = Symbol("$state"), he = Symbol("legacy props"), ge = Symbol(""), S = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), _e = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function ve(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function ye() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function be(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function xe() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Se(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Ce() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function we() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Te(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Ee() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function De() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Oe() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function ke() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function Ae() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function je(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Me() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var C = !1;
function Ne(e) {
	C = e;
}
var w;
function T(e) {
	if (e === null) throw je(), r;
	return w = e;
}
function Pe() {
	return T(/* @__PURE__ */ $t(w));
}
function E(e) {
	if (C) {
		if (/* @__PURE__ */ $t(w) !== null) throw je(), r;
		w = e;
	}
}
function Fe(e = 1) {
	if (C) {
		for (var t = e, n = w; t--;) n = /* @__PURE__ */ $t(n);
		w = n;
	}
}
function Ie(e = !0) {
	for (var t = 0, n = w;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ $t(n);
		e && n.remove(), n = i;
	}
}
function Le(e) {
	if (!e || e.nodeType !== 8) throw je(), r;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function Re(e) {
	return e === this.v;
}
function ze(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Be(e) {
	return !ze(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var D = null;
function Ve(e) {
	D = e;
}
function He(e, n = !1, r) {
	D = {
		p: D,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: G,
		l: t && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Ue(e) {
	var t = D, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) mn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, D = t.p, e ?? {};
}
function We() {
	return !t || D !== null && D.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Ge = [];
function Ke() {
	var e = Ge;
	Ge = [], ne(e);
}
function O(e) {
	if (Ge.length === 0 && !at) {
		var t = Ge;
		queueMicrotask(() => {
			t === Ge && Ke();
		});
	}
	Ge.push(e);
}
function qe() {
	for (; Ge.length > 0;) Ke();
}
function Je(e) {
	var t = G;
	if (t === null) return H.f |= pe, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	Ye(e, t);
}
function Ye(e, t) {
	for (; t !== null;) {
		if (t.f & 128) {
			if (!(t.f & 32768)) throw e;
			try {
				t.b.error(e);
				return;
			} catch (t) {
				e = t;
			}
		}
		t = t.parent;
	}
	throw e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var Xe = ~(y | b | v);
function k(e, t) {
	e.f = e.f & Xe | t;
}
function Ze(e) {
	e.f & 512 || e.deps === null ? k(e, v) : k(e, b);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function Qe(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= ue, Qe(t.deps));
}
function $e(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), Qe(e.deps), k(e, v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var et = !1, tt = !1;
function nt(e) {
	var t = tt;
	try {
		return tt = !1, [e(), tt];
	} finally {
		tt = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var A = /* @__PURE__ */ new Set(), j = null, rt = null, M = null, it = null, at = !1, ot = !1, st = null, ct = null, lt = 0, ut = 1, dt = class t {
	id = ut++;
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#e = /* @__PURE__ */ new Set();
	#t = /* @__PURE__ */ new Set();
	#n = /* @__PURE__ */ new Set();
	#r = /* @__PURE__ */ new Map();
	#i = /* @__PURE__ */ new Map();
	#a = null;
	#o = [];
	#s = [];
	#c = /* @__PURE__ */ new Set();
	#l = /* @__PURE__ */ new Set();
	#u = /* @__PURE__ */ new Map();
	#d = /* @__PURE__ */ new Set();
	is_fork = !1;
	#f = !1;
	#p = /* @__PURE__ */ new Set();
	#m() {
		return this.is_fork || this.#i.size > 0;
	}
	#h() {
		for (let n of this.#p) for (let r of n.#i.keys()) {
			for (var e = !1, t = r; t.parent !== null;) {
				if (this.#u.has(t)) {
					e = !0;
					break;
				}
				t = t.parent;
			}
			if (!e) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#u.has(e) || this.#u.set(e, {
			d: [],
			m: []
		}), this.#d.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#u.get(e);
		if (n) {
			this.#u.delete(e);
			for (var r of n.d) k(r, y), t(r);
			for (r of n.m) k(r, b), t(r);
		}
		this.#d.add(e);
	}
	#g() {
		if (lt++ > 1e3 && (A.delete(this), pt()), !this.#m()) {
			for (let e of this.#c) this.#l.delete(e), k(e, y), this.schedule(e);
			for (let e of this.#l) k(e, b), this.schedule(e);
		}
		let n = this.#o;
		this.#o = [], this.apply();
		var r = st = [], i = [], a = ct = [];
		for (let e of n) try {
			this.#_(e, r, i);
		} catch (t) {
			throw yt(e), t;
		}
		if (j = null, a.length > 0) {
			var o = t.ensure();
			for (let e of a) o.schedule(e);
		}
		if (st = null, ct = null, this.#m() || this.#h()) {
			this.#v(i), this.#v(r);
			for (let [e, t] of this.#u) vt(e, t);
		} else {
			this.#r.size === 0 && A.delete(this), this.#c.clear(), this.#l.clear();
			for (let e of this.#e) e(this);
			this.#e.clear(), rt = this, mt(i), mt(r), rt = null, this.#a?.resolve();
		}
		var s = j;
		if (this.#o.length > 0) {
			let e = s ??= this;
			e.#o.push(...this.#o.filter((t) => !e.#o.includes(t)));
		}
		s !== null && (A.add(s), s.#g()), e && !A.has(this) && this.#y();
	}
	#_(t, n, r) {
		t.f ^= v;
		for (var i = t.first; i !== null;) {
			var a = i.f, o = (a & 96) != 0;
			if (!(o && a & 1024 || a & 8192 || this.#u.has(i)) && i.fn !== null) {
				o ? i.f ^= v : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : Un(i) && (a & 16 && this.#l.add(i), Jn(i));
				var s = i.first;
				if (s !== null) {
					i = s;
					continue;
				}
			}
			for (; i !== null;) {
				var c = i.next;
				if (c !== null) {
					i = c;
					break;
				}
				i = i.parent;
			}
		}
	}
	#v(e) {
		for (var t = 0; t < e.length; t += 1) $e(e[t], this.#c, this.#l);
	}
	capture(e, t, n = !1) {
		e.v !== i && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), M?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		j = this;
	}
	deactivate() {
		j = null, M = null;
	}
	flush() {
		try {
			ot = !0, j = this, this.#g();
		} finally {
			lt = 0, it = null, st = null, ct = null, ot = !1, j = null, M = null, Lt.clear();
		}
	}
	discard() {
		for (let e of this.#t) e(this);
		this.#t.clear(), this.#n.clear(), A.delete(this);
	}
	register_created_effect(e) {
		this.#s.push(e);
	}
	#y() {
		for (let l of A) {
			var e = l.id < this.id, t = [];
			for (let [r, [i, a]] of this.current) {
				if (l.current.has(r)) {
					var n = l.current.get(r)[0];
					if (e && i !== n) l.current.set(r, [i, a]);
					else continue;
				}
				t.push(r);
			}
			var r = [...l.current.keys()].filter((e) => !this.current.has(e));
			if (r.length === 0) e && l.discard();
			else if (t.length > 0) {
				if (e) for (let e of this.#d) l.unskip_effect(e, (e) => {
					e.f & 4194320 ? l.schedule(e) : l.#v([e]);
				});
				l.activate();
				var i = /* @__PURE__ */ new Set(), a = /* @__PURE__ */ new Map();
				for (var o of t) ht(o, r, i, a);
				a = /* @__PURE__ */ new Map();
				var s = [...l.current.keys()].filter((e) => this.current.has(e) ? this.current.get(e)[0] !== e : !0);
				for (let e of this.#s) !(e.f & 155648) && gt(e, s, a) && (e.f & 4194320 ? (k(e, y), l.schedule(e)) : l.#c.add(e));
				if (l.#o.length > 0) {
					l.apply();
					for (var c of l.#o) l.#_(c, [], []);
					l.#o = [];
				}
				l.deactivate();
			}
		}
		for (let e of A) e.#p.has(this) && (e.#p.delete(this), e.#p.size === 0 && !e.#m() && (e.activate(), e.#g()));
	}
	increment(e, t) {
		let n = this.#r.get(t) ?? 0;
		if (this.#r.set(t, n + 1), e) {
			let e = this.#i.get(t) ?? 0;
			this.#i.set(t, e + 1);
		}
	}
	decrement(e, t, n) {
		let r = this.#r.get(t) ?? 0;
		if (r === 1 ? this.#r.delete(t) : this.#r.set(t, r - 1), e) {
			let e = this.#i.get(t) ?? 0;
			e === 1 ? this.#i.delete(t) : this.#i.set(t, e - 1);
		}
		this.#f || n || (this.#f = !0, O(() => {
			this.#f = !1, this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#c.add(t);
		for (let e of t) this.#l.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#e.add(e);
	}
	ondiscard(e) {
		this.#t.add(e);
	}
	on_fork_commit(e) {
		this.#n.add(e);
	}
	run_fork_commit_callbacks() {
		for (let e of this.#n) e(this);
		this.#n.clear();
	}
	settled() {
		return (this.#a ??= re()).promise;
	}
	static ensure() {
		if (j === null) {
			let e = j = new t();
			ot || (A.add(j), at || O(() => {
				j === e && e.flush();
			}));
		}
		return j;
	}
	apply() {
		if (!e || !this.is_fork && A.size === 1) {
			M = null;
			return;
		}
		M = /* @__PURE__ */ new Map();
		for (let [e, [t]] of this.current) M.set(e, t);
		for (let e of A) if (!(e === this || e.is_fork)) {
			var t = !1, n = !1;
			if (e.id < this.id) for (let [r, [, i]] of e.current) i || (t ||= this.current.has(r), n ||= !this.current.has(r));
			if (t && n) this.#p.add(e);
			else for (let [t, n] of e.previous) M.has(t) || M.set(t, n);
		}
	}
	schedule(t) {
		if (it = t, t.b?.is_pending && t.f & 16777228 && !(t.f & 32768)) {
			t.b.defer_effect(t);
			return;
		}
		for (var n = t; n.parent !== null;) {
			n = n.parent;
			var r = n.f;
			if (st !== null && n === G && (e || (H === null || !(H.f & 2)) && !et)) return;
			if (r & 96) {
				if (!(r & 1024)) return;
				n.f ^= v;
			}
		}
		this.#o.push(n);
	}
};
function ft(e) {
	var t = at;
	at = !0;
	try {
		var n;
		for (e && (j !== null && !j.is_fork && j.flush(), n = e());;) {
			if (qe(), j === null) return n;
			j.flush();
		}
	} finally {
		at = t;
	}
}
function pt() {
	try {
		Ce();
	} catch (e) {
		Ye(e, it);
	}
}
var N = null;
function mt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Un(r) && (N = /* @__PURE__ */ new Set(), Jn(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && Dn(r), N?.size > 0)) {
				Lt.clear();
				for (let e of N) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) N.has(n) && (N.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || Jn(n);
					}
				}
				N.clear();
			}
		}
		N = null;
	}
}
function ht(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? ht(i, t, n, r) : e & 4194320 && !(e & 2048) && gt(i, t, r) && (k(i, y), _t(i));
	}
}
function gt(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (c.call(t, r)) return !0;
		if (r.f & 2 && gt(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function _t(e) {
	j.schedule(e);
}
function vt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), k(e, v);
		for (var n = e.first; n !== null;) vt(n, t), n = n.next;
	}
}
function yt(e) {
	k(e, v);
	for (var t = e.first; t !== null;) yt(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function bt(e) {
	let t = 0, n = zt(0), r;
	return () => {
		dn() && (Z(n), bn(() => (t === 0 && (r = Qn(() => e(() => Ut(n)))), t += 1, () => {
			O(() => {
				--t, t === 0 && (r?.(), r = void 0, Ut(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var xt = ce | x;
function St(e, t, n, r) {
	new Ct(e, t, n, r);
}
var Ct = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = C ? w : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Set();
	#m = null;
	#h = bt(() => (this.#m = zt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = G;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = G.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = Sn(() => {
			if (C) {
				let e = this.#t;
				Pe();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#v() : this.#g();
			} else this.#y();
		}, xt), C && (this.#e = w);
	}
	#g() {
		try {
			this.#a = z(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed;
		t && (this.#s = z(() => {
			t(this.#e, () => e, () => () => {});
		}));
	}
	#v() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = z(() => e(this.#e)), O(() => {
			var e = this.#c = document.createDocumentFragment(), t = Zt();
			e.append(t), this.#a = this.#x(() => z(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, On(this.#o, () => {
				this.#o = null;
			}), this.#b(j));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = z(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Mn(this.#a, e);
				let t = this.#n.pending;
				this.#o = z(() => t(this.#e));
			} else this.#b(j);
		} catch (e) {
			this.error(e);
		}
	}
	#b(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		$e(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = G, n = H, r = D;
		K(this.#i), W(this.#i), Ve(this.#i.ctx);
		try {
			return dt.ensure(), e();
		} catch (e) {
			return Je(e), null;
		} finally {
			K(t), W(n), Ve(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && On(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, O(() => {
			this.#d = !1, this.#m && Vt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Z(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		j?.is_fork ? (this.#a && j.skip_effect(this.#a), this.#o && j.skip_effect(this.#o), this.#s && j.skip_effect(this.#s), j.on_fork_commit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (B(this.#a), null), this.#o &&= (B(this.#o), null), this.#s &&= (B(this.#s), null), C && (T(this.#t), Fe(), T(Ie()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				Me();
				return;
			}
			r = !0, i && ke(), this.#s !== null && On(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#y();
			});
		}, o = (e) => {
			try {
				i = !0, t?.(e, a), i = !1;
			} catch (e) {
				Ye(e, this.#i && this.#i.parent);
			}
			n && (this.#s = this.#x(() => {
				try {
					return z(() => {
						var t = G;
						t.b = this, t.f |= 128, n(this.#e, () => e, () => a);
					});
				} catch (e) {
					return Ye(e, this.#i.parent), null;
				}
			}));
		};
		O(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				Ye(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(o, (e) => Ye(e, this.#i && this.#i.parent)) : o(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function wt(e, t, n, r) {
	let i = We() ? Ot : At;
	var a = e.filter((e) => !e.settled);
	if (n.length === 0 && a.length === 0) {
		r(t.map(i));
		return;
	}
	var o = G, s = Tt(), c = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function l(e) {
		s();
		try {
			r(e);
		} catch (e) {
			o.f & 16384 || Ye(e, o);
		}
		Et();
	}
	if (n.length === 0) {
		c.then(() => l(t.map(i)));
		return;
	}
	var u = Dt();
	function d() {
		Promise.all(n.map((e) => /* @__PURE__ */ kt(e))).then((e) => l([...t.map(i), ...e])).catch((e) => Ye(e, o)).finally(() => u());
	}
	c ? c.then(() => {
		s(), d(), Et();
	}) : d();
}
function Tt() {
	var e = G, t = H, n = D, r = j;
	return function(i = !0) {
		K(e), W(t), Ve(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function Et(e = !0) {
	K(null), W(null), Ve(null), e && j?.deactivate();
}
function Dt() {
	var e = G, t = e.b, n = j, r = t.is_rendered();
	return t.update_pending_count(1, n), n.increment(r, e), (i = !1) => {
		t.update_pending_count(-1, n), n.decrement(r, e, i);
	};
}
/* @__NO_SIDE_EFFECTS__ */
function Ot(e) {
	var t = 2 | y;
	return G !== null && (G.f |= x), {
		ctx: D,
		deps: null,
		effects: null,
		equals: Re,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: i,
		wv: 0,
		parent: G,
		ac: null
	};
}
/* @__NO_SIDE_EFFECTS__ */
function kt(e, t, n) {
	let r = G;
	r === null && ye();
	var a = void 0, o = zt(i), s = !H, c = /* @__PURE__ */ new Map();
	return yn(() => {
		var t = G, n = re();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, n.reject).finally(Et);
		} catch (e) {
			n.reject(e), Et();
		}
		var i = j;
		if (s) {
			if (t.f & 32768) var l = Dt();
			if (r.b.is_rendered()) c.get(i)?.reject(S), c.delete(i);
			else {
				for (let e of c.values()) e.reject(S);
				c.clear();
			}
			c.set(i, n);
		}
		let u = (e, n = void 0) => {
			if (l && l(n === S), !(n === S || t.f & 16384)) {
				if (i.activate(), n) o.f |= pe, Vt(o, n);
				else {
					o.f & 8388608 && (o.f ^= pe), Vt(o, e);
					for (let [e, t] of c) {
						if (c.delete(e), e === i) break;
						t.reject(S);
					}
				}
				i.deactivate();
			}
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), fn(() => {
		for (let e of c.values()) e.reject(S);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === a ? e(o) : t(a);
			}
			n.then(r, r);
		}
		t(a);
	});
}
/* @__NO_SIDE_EFFECTS__ */
function At(e) {
	let t = /* @__PURE__ */ Ot(e);
	return t.equals = Be, t;
}
function jt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) B(t[n]);
	}
}
function Mt(e) {
	var t, n = G, r = e.parent;
	if (!V && r !== null && r.f & 24576) return Ae(), e.v;
	K(r);
	try {
		e.f &= ~ue, jt(e), t = Gn(e);
	} finally {
		K(n);
	}
	return t;
}
function Nt(e) {
	var t = Mt(e);
	if (!e.equals(t) && (e.wv = Hn(), (!j?.is_fork || e.deps === null) && (j === null ? e.v = t : j.capture(e, t, !0), e.deps === null))) {
		k(e, v);
		return;
	}
	V || (M === null ? Ze(e) : (dn() || j?.is_fork) && M.set(e, t));
}
function Pt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(S), t.teardown = _, t.ac = null, qn(t, 0), wn(t));
}
function Ft(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && Jn(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var It = /* @__PURE__ */ new Set(), Lt = /* @__PURE__ */ new Map(), Rt = !1;
function zt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Re,
		rv: 0,
		wv: 0
	};
}
/* @__NO_SIDE_EFFECTS__ */
function Bt(e, t) {
	let n = zt(e, t);
	return In(n), n;
}
/* @__NO_SIDE_EFFECTS__ */
function P(e, n = !1, r = !0) {
	let i = zt(e);
	return n || (i.equals = Be), t && r && D !== null && D.l !== null && (D.l.s ??= []).push(i), i;
}
function F(e, t, n = !1) {
	return H !== null && (!U || H.f & 131072) && We() && H.f & 4325394 && (q === null || !c.call(q, e)) && Oe(), Vt(e, n ? Gt(t) : t, ct);
}
function Vt(e, t, n = null) {
	if (!e.equals(t)) {
		Lt.set(e, V ? t : e.v);
		var r = dt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Mt(t), M === null && Ze(t);
		}
		e.wv = Hn(), Wt(e, y, n), We() && G !== null && G.f & 1024 && !(G.f & 96) && (X === null ? Ln([e]) : X.push(e)), !r.is_fork && It.size > 0 && !Rt && Ht();
	}
	return t;
}
function Ht() {
	Rt = !1;
	for (let e of It) e.f & 1024 && k(e, b), Un(e) && Jn(e);
	It.clear();
}
function Ut(e) {
	F(e, e.v + 1);
}
function Wt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = We(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === G)) {
			var l = (c & y) === 0;
			if (l && k(s, t), c & 2) {
				var u = s;
				M?.delete(u), c & 65536 || (c & 512 && (s.f |= ue), Wt(u, b, n));
			} else if (l) {
				var d = s;
				c & 16 && N !== null && N.add(d), n === null ? _t(d) : n.push(d);
			}
		}
	}
}
function Gt(e) {
	if (typeof e != "object" || !e || me in e) return e;
	let t = g(e);
	if (t !== m && t !== h) return e;
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ Bt(0), s = null, c = Bn, l = (e) => {
		if (Bn === c) return e();
		var t = H, n = Bn;
		W(null), Vn(c);
		var r = e();
		return W(t), Vn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ Bt(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && Ee();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ Bt(r.value, s);
				return n.set(t, e), e;
			}) : F(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ Bt(i, s));
					n.set(t, e), Ut(a);
				}
			} else F(r, i), Ut(a);
			return !0;
		},
		get(t, r, a) {
			if (r === me) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || f(t, r)?.writable) && (o = l(() => /* @__PURE__ */ Bt(Gt(c ? t[r] : i), s)), n.set(r, o)), o !== void 0) {
				var u = Z(o);
				return u === i ? void 0 : u;
			}
			return Reflect.get(t, r, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var r = Reflect.getOwnPropertyDescriptor(e, t);
			if (r && "value" in r) {
				var a = n.get(t);
				a && (r.value = Z(a));
			} else if (r === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== i) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === me) return !0;
			var r = n.get(t), a = r !== void 0 && r.v !== i || Reflect.has(e, t);
			return (r !== void 0 || G !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ Bt(a ? Gt(e[t]) : i, s)), n.set(t, r)), Z(r) === i) ? !1 : a;
		},
		set(e, t, o, c) {
			var u = n.get(t), d = t in e;
			if (r && t === "length") for (var p = o; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ Bt(i, s)), n.set(p + "", m)) : F(m, i);
			}
			if (u === void 0) (!d || f(e, t)?.writable) && (u = l(() => /* @__PURE__ */ Bt(void 0, s)), F(u, Gt(o)), n.set(t, u));
			else {
				d = u.v !== i;
				var h = l(() => Gt(o));
				F(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, o), !d) {
				if (r && typeof t == "string") {
					var ee = n.get("length"), _ = Number(t);
					Number.isInteger(_) && _ >= ee.v && F(ee, _ + 1);
				}
				Ut(a);
			}
			return !0;
		},
		ownKeys(e) {
			Z(a);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== i;
			});
			for (var [r, o] of n) o.v !== i && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			De();
		}
	});
}
var Kt, qt, Jt, Yt;
function Xt() {
	if (Kt === void 0) {
		Kt = window, qt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		Jt = f(t, "firstChild").get, Yt = f(t, "nextSibling").get, ee(e) && (e.__click = void 0, e.__className = void 0, e.__attributes = null, e.__style = void 0, e.__e = void 0), ee(n) && (n.__t = void 0);
	}
}
function Zt(e = "") {
	return document.createTextNode(e);
}
/* @__NO_SIDE_EFFECTS__ */
function Qt(e) {
	return Jt.call(e);
}
/* @__NO_SIDE_EFFECTS__ */
function $t(e) {
	return Yt.call(e);
}
function I(e, t) {
	if (!C) return /* @__PURE__ */ Qt(e);
	var n = /* @__PURE__ */ Qt(w);
	if (n === null) n = w.appendChild(Zt());
	else if (t && n.nodeType !== 3) {
		var r = Zt();
		return n?.before(r), T(r), r;
	}
	return t && rn(n), T(n), n;
}
function L(e, t = 1, n = !1) {
	let r = C ? w : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ $t(r);
	if (!C) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = Zt();
			return r === null ? i?.after(a) : r.before(a), T(a), a;
		}
		rn(r);
	}
	return T(r), r;
}
function en(e) {
	e.textContent = "";
}
function tn() {
	return !e || N !== null ? !1 : (G.f & oe) !== 0;
}
function nn(e, t, n) {
	let r = n ? { is: n } : void 0;
	return document.createElementNS(t ?? "http://www.w3.org/1999/xhtml", e, r);
}
function rn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var an = !1;
function on() {
	an || (an = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t.__on_r?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function sn(e) {
	var t = H, n = G;
	W(null), K(null);
	try {
		return e();
	} finally {
		W(t), K(n);
	}
}
function cn(e, t, n, r = n) {
	e.addEventListener(t, () => sn(n));
	let i = e.__on_r;
	i ? e.__on_r = () => {
		i(), r(!0);
	} : e.__on_r = () => r(!0), on();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function ln(e) {
	G === null && (H === null && Se(e), xe()), V && be(e);
}
function un(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function R(e, t) {
	var n = G;
	n !== null && n.f & 8192 && (e |= ie);
	var r = {
		ctx: D,
		deps: null,
		nodes: null,
		f: e | y | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	j?.register_created_effect(r);
	var i = r;
	if (e & 4) st === null ? dt.ensure().schedule(r) : st.push(r);
	else if (t !== null) {
		try {
			Jn(r);
		} catch (e) {
			throw B(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= ce));
	}
	if (i !== null && (i.parent = n, n !== null && un(i, n), H !== null && H.f & 2 && !(e & 64))) {
		var a = H;
		(a.effects ??= []).push(i);
	}
	return r;
}
function dn() {
	return H !== null && !U;
}
function fn(e) {
	let t = R(8, null);
	return k(t, v), t.teardown = e, t;
}
function pn(e) {
	ln("$effect");
	var t = G.f;
	if (!H && t & 32 && !(t & 32768)) {
		var n = D;
		(n.e ??= []).push(e);
	} else return mn(e);
}
function mn(e) {
	return R(4 | le, e);
}
function hn(e) {
	return ln("$effect.pre"), R(8 | le, e);
}
function gn(e) {
	dt.ensure();
	let t = R(64 | x, e);
	return () => {
		B(t);
	};
}
function _n(e) {
	dt.ensure();
	let t = R(64 | x, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? On(t, () => {
			B(t), n(void 0);
		}) : (B(t), n(void 0));
	});
}
function vn(e) {
	return R(4, e);
}
function yn(e) {
	return R(fe | x, e);
}
function bn(e, t = 0) {
	return R(8 | t, e);
}
function xn(e, t = [], n = [], r = []) {
	wt(r, t, n, (t) => {
		R(8, () => e(...t.map(Z)));
	});
}
function Sn(e, t = 0) {
	return R(16 | t, e);
}
function z(e) {
	return R(32 | x, e);
}
function Cn(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = V, n = H;
		Fn(!0), W(null);
		try {
			t.call(null);
		} finally {
			Fn(e), W(n);
		}
	}
}
function wn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && sn(() => {
			e.abort(S);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : B(n, t), n = r;
	}
}
function Tn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || B(t), t = n;
	}
}
function B(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (En(e.nodes.start, e.nodes.end), n = !0), k(e, se), wn(e, t && !n), qn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Cn(e), e.f ^= se, e.f |= ae;
	var i = e.parent;
	i !== null && i.first !== null && Dn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function En(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ $t(e);
		e.remove(), e = n;
	}
}
function Dn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function On(e, t, n = !0) {
	var r = [];
	kn(e, r, !0);
	var i = () => {
		n && B(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function kn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ie;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				kn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function An(e) {
	jn(e, !0);
}
function jn(e, t) {
	if (e.f & 8192) {
		e.f ^= ie, e.f & 1024 || (k(e, y), dt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			jn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Mn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ $t(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Nn = null, Pn = !1, V = !1;
function Fn(e) {
	V = e;
}
var H = null, U = !1;
function W(e) {
	H = e;
}
var G = null;
function K(e) {
	G = e;
}
var q = null;
function In(t) {
	H !== null && (!e || H.f & 2) && (q === null ? q = [t] : q.push(t));
}
var J = null, Y = 0, X = null;
function Ln(e) {
	X = e;
}
var Rn = 1, zn = 0, Bn = zn;
function Vn(e) {
	Bn = e;
}
function Hn() {
	return ++Rn;
}
function Un(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~ue), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Un(a) && Nt(a), a.wv > e.wv) return !0;
		}
		t & 512 && M === null && k(e, v);
	}
	return !1;
}
function Wn(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && q !== null && c.call(q, t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? Wn(o, n, !1) : n === o && (r ? k(o, y) : o.f & 1024 && k(o, b), _t(o));
	}
}
function Gn(e) {
	var t = J, n = Y, r = X, i = H, a = q, o = D, s = U, c = Bn, l = e.f;
	J = null, Y = 0, X = null, H = l & 96 ? null : e, q = null, Ve(e.ctx), U = !1, Bn = ++zn, e.ac !== null && (sn(() => {
		e.ac.abort(S);
	}), e.ac = null);
	try {
		e.f |= de;
		var u = e.fn, d = u();
		e.f |= oe;
		var f = e.deps, p = j?.is_fork;
		if (J !== null) {
			var m;
			if (p || qn(e, Y), f !== null && Y > 0) for (f.length = Y + J.length, m = 0; m < J.length; m++) f[Y + m] = J[m];
			else e.deps = f = J;
			if (dn() && e.f & 512) for (m = Y; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && Y < f.length && (qn(e, Y), f.length = Y);
		if (We() && X !== null && !U && f !== null && !(e.f & 6146)) for (m = 0; m < X.length; m++) Wn(X[m], e);
		if (i !== null && i !== e) {
			if (zn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = zn;
			if (t !== null) for (let e of t) e.rv = zn;
			X !== null && (r === null ? r = X : r.push(...X));
		}
		return e.f & 8388608 && (e.f ^= pe), d;
	} catch (e) {
		return Je(e);
	} finally {
		e.f ^= de, J = t, Y = n, X = r, H = i, q = a, Ve(o), U = s, Bn = c;
	}
}
function Kn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var r = s.call(n, e);
		if (r !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[r] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (J === null || !c.call(J, t))) {
		var o = t;
		o.f & 512 && (o.f ^= 512, o.f &= ~ue), o.v !== i && Ze(o), Pt(o), qn(o, 0);
	}
}
function qn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Kn(e, n[r]);
}
function Jn(e) {
	var t = e.f;
	if (!(t & 16384)) {
		k(e, v);
		var n = G, r = Pn;
		G = e, Pn = !0;
		try {
			t & 16777232 ? Tn(e) : wn(e), Cn(e);
			var i = Gn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Rn;
		} finally {
			Pn = r, G = n;
		}
	}
}
async function Yn() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), ft();
}
function Z(e) {
	var t = (e.f & 2) != 0;
	if (Nn?.add(e), H !== null && !U && !(G !== null && G.f & 16384) && (q === null || !c.call(q, e))) {
		var n = H.deps;
		if (H.f & 2097152) e.rv < zn && (e.rv = zn, J === null && n !== null && n[Y] === e ? Y++ : J === null ? J = [e] : J.push(e));
		else {
			(H.deps ??= []).push(e);
			var r = e.reactions;
			r === null ? e.reactions = [H] : c.call(r, H) || r.push(H);
		}
	}
	if (V && Lt.has(e)) return Lt.get(e);
	if (t) {
		var i = e;
		if (V) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || Zn(i)) && (a = Mt(i)), Lt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !U && H !== null && (Pn || (H.f & 512) != 0), s = (i.f & oe) === 0;
		Un(i) && (o && (i.f |= 512), Nt(i)), o && !s && (Ft(i), Xn(i));
	}
	if (M?.has(e)) return M.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function Xn(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Ft(t), Xn(t));
}
function Zn(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Lt.has(t) || t.f & 2 && Zn(t)) return !0;
	return !1;
}
function Qn(e) {
	var t = U;
	try {
		return U = !0, e();
	} finally {
		U = t;
	}
}
function $n(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (me in e) er(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && me in n && er(n);
		}
	}
}
function er(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			er(e[n], t);
		} catch {}
		let n = g(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = p(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/events.js
var tr = Symbol("events"), nr = /* @__PURE__ */ new Set(), rr = /* @__PURE__ */ new Set();
function ir(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || sr.call(t, e), !e.cancelBubble) return sn(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? O(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function ar(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = ir(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && fn(() => {
		t.removeEventListener(e, o, a);
	});
}
var or = null;
function sr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	or = e;
	var o = 0, s = or === e && e[tr];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[tr] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		d(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var u = H, f = G;
		W(null), K(null);
		try {
			for (var p, m = []; a !== null;) {
				var h = a.assignedSlot || a.parentNode || a.host || null;
				try {
					var g = a[tr]?.[r];
					g != null && (!a.disabled || e.target === a) && g.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble || h === t || h === null) break;
				a = h;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[tr] = t, delete e.currentTarget, W(u), K(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var cr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function lr(e) {
	return cr?.createHTML(e) ?? e;
}
function ur(e) {
	var t = nn("template");
	return t.innerHTML = lr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function dr(e, t) {
	var n = G;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/* @__NO_SIDE_EFFECTS__ */
function Q(e, t) {
	var n = (t & 1) != 0, r = (t & 2) != 0, i, a = !e.startsWith("<!>");
	return () => {
		if (C) return dr(w, null), w;
		i === void 0 && (i = ur(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ Qt(i)));
		var t = r || qt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ Qt(t), s = t.lastChild;
			dr(o, s);
		} else dr(t, t);
		return t;
	};
}
function $(e, t) {
	if (C) {
		var n = G;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = w), Pe();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var fr = ["touchstart", "touchmove"];
function pr(e) {
	return fr.includes(e);
}
function mr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e.__t ??= e.nodeValue) && (e.__t = n, e.nodeValue = `${n}`);
}
function hr(e, t) {
	return vr(e, t);
}
function gr(e, t) {
	Xt(), t.intro = t.intro ?? !1;
	let n = t.target, i = C, a = w;
	try {
		for (var o = /* @__PURE__ */ Qt(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ $t(o);
		if (!o) throw r;
		Ne(!0), T(o);
		let i = vr(e, {
			...t,
			anchor: o
		});
		return Ne(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && we(), Xt(), en(n), Ne(!1), hr(e, t);
	} finally {
		Ne(i), T(a);
	}
}
var _r = /* @__PURE__ */ new Map();
function vr(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	Xt();
	var u = void 0, d = _n(() => {
		var s = n ?? t.appendChild(Zt());
		St(s, { pending: () => {} }, (t) => {
			He({});
			var n = D;
			if (o && (n.c = o), a && (i.$$events = a), C && dr(t, null), u = e(t, i) || {}, C && (G.nodes.end = w, w === null || w.nodeType !== 8 || w.data !== "]")) throw je(), r;
			Ue();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = pr(r);
					for (let e of [t, document]) {
						var a = _r.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), _r.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, sr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(l(nr)), rr.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = _r.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, sr), r.delete(e), r.size === 0 && _r.delete(n)) : r.set(e, i);
			}
			rr.delete(f), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return yr.set(u, d), u;
}
var yr = /* @__PURE__ */ new WeakMap();
function br(e, t) {
	let n = yr.get(e);
	return n ? (yr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var xr = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) An(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (B(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						Mn(r, t), t.append(Zt()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else B(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), On(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (B(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = j, r = tn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = Zt();
			i.append(a), this.#n.set(e, {
				effect: z(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, z(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else C && (this.anchor = w), this.#a(n);
	}
};
function Sr(e) {
	D === null && ve("onMount"), t && D.l !== null ? Cr(D).m.push(e) : pn(() => {
		let t = Qn(e);
		if (typeof t == "function") return t;
	});
}
function Cr(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function wr(e, t, n = !1) {
	var r;
	C && (r = w, Pe());
	var i = new xr(e), a = n ? ce : 0;
	function o(e, t) {
		if (C) {
			var n = Le(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Ie();
				T(a), i.anchor = a, Ne(!1), i.ensure(e, t), Ne(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	Sn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Tr(e, t) {
	vn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = nn("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Er = Symbol("is custom element"), Dr = Symbol("is html"), Or = _e ? "link" : "LINK";
function kr(e) {
	if (C) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Ar(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Ar(e, "checked", null), e.checked = r;
				}
			}
		};
		e.__on_r = n, O(n), on();
	}
}
function Ar(e, t, n, r) {
	var i = Mr(e);
	C && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Or) || i[t] !== (i[t] = n) && (t === "loading" && (e[ge] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Pr(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function jr(e, t, n) {
	var r = H, i = G;
	let a = C;
	C && Ne(!1), W(null), K(null);
	try {
		t !== "style" && (Nr.has(e.getAttribute("is") || e.nodeName) || !customElements || customElements.get(e.getAttribute("is") || e.nodeName.toLowerCase()) ? Pr(e).includes(t) : n && typeof n == "object") ? e[t] = n : Ar(e, t, n == null ? n : String(n));
	} finally {
		W(r), K(i), a && Ne(!0);
	}
}
function Mr(e) {
	return e.__attributes ??= {
		[Er]: e.nodeName.includes("-"),
		[Dr]: e.namespaceURI === a
	};
}
var Nr = /* @__PURE__ */ new Map();
function Pr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Nr.get(t);
	if (n) return n;
	Nr.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Fr(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	cn(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = Ir(t) ? Lr(a) : a, r(a), j !== null && i.add(j), await Yn(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (C && t.defaultValue !== t.value || Qn(n) == null && t.value) && (r(Ir(t) ? Lr(t.value) : t.value), j !== null && i.add(j)), bn(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? rt : j;
			if (i.has(a)) return;
		}
		Ir(t) && r === Lr(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function Ir(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Lr(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function Rr(e = !1) {
	let t = D, n = t.l.u;
	if (!n) return;
	let r = () => $n(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ Ot(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Z(i);
	}
	n.b.length && hn(() => {
		zr(t, r), ne(n.b);
	}), pn(() => {
		let e = Qn(() => n.m.map(te));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && pn(() => {
		zr(t, r), ne(n.a);
	});
}
function zr(e, t) {
	if (e.l.s) for (let t of e.l.s) Z(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function Br(e, n, r, i) {
	var a = !t || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = () => (l && (l = !1, c = s ? Qn(i) : i), c);
	let d;
	if (o) {
		var p = me in e || he in e;
		d = f(e, n)?.set ?? (p && n in e ? (t) => e[n] = t : void 0);
	}
	var m, h = !1;
	o ? [m, h] = nt(() => e[n]) : m = e[n], m === void 0 && i !== void 0 && (m = u(), d && (a && Te(n), d(m)));
	var g = a ? () => {
		var t = e[n];
		return t === void 0 ? u() : (l = !0, t);
	} : () => {
		var t = e[n];
		return t !== void 0 && (c = void 0), t === void 0 ? c : t;
	};
	if (a && !(r & 4)) return g;
	if (d) {
		var ee = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || ee || h) && d(t ? g() : e), e) : g();
		});
	}
	var _ = !1, te = (r & 1 ? Ot : At)(() => (_ = !1, g()));
	o && Z(te);
	var ne = G;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Z(te) : a && o ? Gt(e) : e;
			return F(te, n), _ = !0, c !== void 0 && (c = n), e;
		}
		return V && _ || ne.f & 16384 ? te.v : Z(te);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function Vr(e) {
	return new Hr(e);
}
var Hr = class {
	#e;
	#t;
	constructor(t) {
		var n = /* @__PURE__ */ new Map(), r = (e, t) => {
			var r = /* @__PURE__ */ P(t, !1, !1);
			return n.set(e, r), r;
		};
		let i = new Proxy({
			...t.props || {},
			$$events: {}
		}, {
			get(e, t) {
				return Z(n.get(t) ?? r(t, Reflect.get(e, t)));
			},
			has(e, t) {
				return t === he ? !0 : (Z(n.get(t) ?? r(t, Reflect.get(e, t))), Reflect.has(e, t));
			},
			set(e, t, i) {
				return F(n.get(t) ?? r(t, i), i), Reflect.set(e, t, i);
			}
		});
		this.#t = (t.hydrate ? gr : hr)(t.component, {
			target: t.target,
			anchor: t.anchor,
			props: i,
			context: t.context,
			intro: t.intro ?? !1,
			recover: t.recover,
			transformError: t.transformError
		}), !e && (!t?.props?.$$host || t.sync === !1) && ft(), this.#e = i.$$events;
		for (let e of Object.keys(this.#t)) e === "$set" || e === "$destroy" || e === "$on" || d(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(i, e);
		}, this.#t.$destroy = () => {
			br(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, Ur;
typeof HTMLElement == "function" && (Ur = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = nn("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = Gr(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = Wr(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = Vr({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = gn(() => {
				bn(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = Wr(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = Wr(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return u(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function Wr(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function Gr(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function Kr(e, t, n, r, i, a) {
	let o = class extends Ur {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return u(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return u(t).forEach((e) => {
		d(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = Wr(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (f(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		d(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region PlexCard.svelte
var qr = /* @__PURE__ */ Q("<span class=\"status-badge active-server svelte-lueg2f\">● Active</span>"), Jr = /* @__PURE__ */ Q("<span class=\"status-badge authenticated svelte-lueg2f\">✓ Authenticated</span>"), Yr = /* @__PURE__ */ Q("<span class=\"status-badge connected svelte-lueg2f\">● Connected</span>"), Xr = /* @__PURE__ */ Q("<span class=\"status-badge disconnected svelte-lueg2f\">⚠ Disconnected</span>"), Zr = /* @__PURE__ */ Q("<div class=\"loading svelte-lueg2f\">Loading...</div>"), Qr = /* @__PURE__ */ Q("<button class=\"btn-secondary svelte-lueg2f\"> </button>"), $r = /* @__PURE__ */ Q("<button class=\"btn-secondary svelte-lueg2f\"> </button>"), ei = /* @__PURE__ */ Q("<button class=\"btn-secondary svelte-lueg2f\" disabled=\"\">Waiting for authorization...</button>"), ti = /* @__PURE__ */ Q("<button class=\"btn-primary svelte-lueg2f\">Reauthenticate</button>"), ni = /* @__PURE__ */ Q("<button class=\"btn-primary svelte-lueg2f\">Login with Plex</button>"), ri = /* @__PURE__ */ Q("<div class=\"section svelte-lueg2f\"><h3 class=\"svelte-lueg2f\">Server Configuration</h3> <div class=\"form-group svelte-lueg2f\"><label class=\"svelte-lueg2f\"><span class=\"label-text svelte-lueg2f\">Server URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:32400\" class=\"input svelte-lueg2f\"/> <span class=\"help-text svelte-lueg2f\">Enter your Plex server IP address or URL (include port, typically :32400)</span></label> <label class=\"svelte-lueg2f\"><span class=\"label-text svelte-lueg2f\">Server Name (Optional)</span> <input type=\"text\" placeholder=\"My Plex Server\" class=\"input svelte-lueg2f\"/> <span class=\"help-text svelte-lueg2f\">Preferred server if you have multiple</span></label> <div class=\"border-t border-gray-700 my-4 pt-4\"><echosync-path-mapping-editor></echosync-path-mapping-editor></div> <div class=\"button-group svelte-lueg2f\"><button class=\"btn-primary svelte-lueg2f\"> </button> <!> <!> <!></div></div></div>", 2), ii = /* @__PURE__ */ Q("<section class=\"plex-card card svelte-lueg2f\"><div class=\"card-header svelte-lueg2f\"><div class=\"header-left svelte-lueg2f\"><h2 class=\"svelte-lueg2f\">Plex</h2> <!> <!> <!></div> <button class=\"btn-secondary svelte-lueg2f\"> </button></div> <!></section>"), ai = {
	hash: "svelte-lueg2f",
	code: ".plex-card.svelte-lueg2f {padding:20px;margin-bottom:16px;}.card-header.svelte-lueg2f {display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid var(--border-color, rgba(255,255,255,0.1));}.header-left.svelte-lueg2f {display:flex;align-items:center;gap:12px;}.card-header.svelte-lueg2f h2:where(.svelte-lueg2f) {margin:0;font-size:20px;font-weight:600;}.status-badge.svelte-lueg2f {font-size:12px;padding:4px 8px;border-radius:4px;}.status-badge.connected.svelte-lueg2f {background:rgba(0, 230, 118, 0.2);color:#00e676;}.status-badge.disconnected.svelte-lueg2f {background:rgba(255, 152, 0, 0.2);color:#ff9800;}.status-badge.authenticated.svelte-lueg2f {background:rgba(0, 230, 118, 0.2);color:#00e676;}.status-badge.active-server.svelte-lueg2f {background:rgba(59, 130, 246, 0.2);color:#3b82f6;font-weight:600;}.section.svelte-lueg2f {margin-bottom:24px;}.section.svelte-lueg2f h3:where(.svelte-lueg2f) {margin:0 0 16px 0;font-size:16px;font-weight:600;}.form-group.svelte-lueg2f {display:flex;flex-direction:column;gap:16px;}label.svelte-lueg2f {display:flex;flex-direction:column;gap:6px;}.label-text.svelte-lueg2f {font-size:13px;font-weight:500;color:var(--text-primary);}.help-text.svelte-lueg2f {font-size:12px;color:var(--muted);}.input.svelte-lueg2f {padding:10px 12px;border-radius:6px;border:1px solid var(--border-color, rgba(255,255,255,0.1));background:var(--input-bg, rgba(0,0,0,0.2));color:var(--text-primary);font-size:14px;}.input.svelte-lueg2f:focus {outline:none;border-color:var(--primary, #00e676);}.button-group.svelte-lueg2f {display:flex;gap:12px;flex-wrap:wrap;}.btn-primary.svelte-lueg2f, .btn-secondary.svelte-lueg2f {padding:10px 20px;border-radius:6px;border:none;font-size:14px;font-weight:500;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-lueg2f {background:var(--primary, #00e676);color:#000;}.btn-primary.svelte-lueg2f:hover:not(:disabled) {background:var(--primary-hover, #00d368);}.btn-secondary.svelte-lueg2f {background:transparent;color:var(--text-primary);border:1px solid var(--border-color, rgba(255,255,255,0.2));}.btn-secondary.svelte-lueg2f:hover:not(:disabled) {background:rgba(255,255,255,0.05);}.btn-primary.svelte-lueg2f:disabled, .btn-secondary.svelte-lueg2f:disabled {opacity:0.5;cursor:not-allowed;}.loading.svelte-lueg2f {padding:20px;text-align:center;color:var(--muted);}\n\n  @keyframes svelte-lueg2f-spin {\n    to { transform: rotate(360deg); }\n  }"
};
function oi(e, t) {
	He(t, !1), Tr(e, ai);
	let n = Br(t, "apiBase", 12, ""), r = /* @__PURE__ */ P(""), i = /* @__PURE__ */ P(""), a = /* @__PURE__ */ P([]), o = /* @__PURE__ */ P(!1), s = /* @__PURE__ */ P(!1), c = /* @__PURE__ */ P(!0), l = /* @__PURE__ */ P(!1), u = /* @__PURE__ */ P(!1), d = /* @__PURE__ */ P(!1), f = null, p = null, m = /* @__PURE__ */ P(!1), h = /* @__PURE__ */ P(!1), g = /* @__PURE__ */ P(!1);
	Sr(async () => {
		await _(), F(c, !1);
	});
	async function ee() {
		try {
			F(g, !0), await fetch(`${n()}/plex/activate`, { method: "POST" }), console.log("Plex activated as media server"), await _();
		} catch (e) {
			console.error("Failed to activate server:", e), console.error("Failed to activate server");
		} finally {
			F(g, !1);
		}
	}
	async function _() {
		try {
			let e = await fetch(`${n()}/plex/settings`);
			e.data?.settings && (F(r, e.data.settings.base_url || ""), F(i, e.data.settings.server_name || ""), F(a, e.data.settings.path_mappings || []), F(o, e.data.settings.has_token || !1), F(s, e.data.settings.connected || !1), F(h, e.data.settings.is_active || !1));
		} catch (e) {
			console.error("Failed to load Plex settings:", e), console.error("Failed to load Plex settings");
		}
	}
	async function te() {
		if (!Z(r).trim()) {
			console.error("Server URL is required");
			return;
		}
		try {
			F(l, !0), await fetch(`${n()}/plex/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					base_url: Z(r),
					server_name: Z(i),
					path_mappings: Z(a)
				})
			}), console.log("Plex settings saved"), await _();
		} catch (e) {
			console.error("Failed to save Plex settings:", e), console.error("Failed to save settings");
		} finally {
			F(l, !1);
		}
	}
	async function ne() {
		try {
			F(d, !0);
			let e = await fetch(`${n()}/plex/auth/start`, { method: "POST" });
			e.data?.oauth_url && e.data?.session_id && (f = e.data.session_id, window.open(e.data.oauth_url, "PlexOAuth", "width=600,height=700"), p = setInterval(async () => {
				try {
					(await fetch(`${n()}/plex/auth/poll/${f}`)).data?.completed && (clearInterval(p), p = null, console.log("Plex authentication successful"), F(d, !1), f = null, localStorage.removeItem("plex_oauth_session"), await _());
				} catch (e) {
					console.error("OAuth poll error:", e), e.response && e.response.status === 404 && (clearInterval(p), p = null, F(d, !1), f = null, localStorage.removeItem("plex_oauth_session"), console.error("Authentication session expired or server restarted"));
				}
			}, 2e3), setTimeout(() => {
				p && (clearInterval(p), p = null, F(d, !1), f = null, console.error("OAuth timeout - please try again"));
			}, 6e5));
		} catch (e) {
			console.error("Failed to start Plex OAuth:", e), console.error("Failed to start authentication"), F(d, !1);
		}
	}
	async function re() {
		if (f && p) {
			clearInterval(p), p = null;
			try {
				await fetch(`${n()}/plex/auth/cancel/${f}`, { method: "DELETE" });
			} catch (e) {
				console.error("Failed to cancel OAuth:", e);
			}
			f = null, F(d, !1), console.log("Authentication cancelled");
		}
	}
	async function v() {
		try {
			F(u, !0);
			let e = await fetch(`${n()}/plex/test-connection`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ base_url: Z(r) })
			});
			e.data?.connected && (console.log(`Connected to ${e.data.server_name}`), await _());
		} catch (e) {
			console.error("Connection test failed:", e);
			let t = e?.response?.data?.error || "Connection failed";
			console.error(t);
		} finally {
			F(u, !1);
		}
	}
	var y = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), ft();
		}
	};
	Rr();
	var b = ii(), ie = I(b), ae = I(ie), oe = L(I(ae), 2), se = (e) => {
		$(e, qr());
	};
	wr(oe, (e) => {
		Z(h) && e(se);
	});
	var ce = L(oe, 2), x = (e) => {
		$(e, Jr());
	};
	wr(ce, (e) => {
		Z(o) && e(x);
	});
	var le = L(ce, 2), ue = (e) => {
		$(e, Yr());
	}, de = (e) => {
		$(e, Xr());
	};
	wr(le, (e) => {
		Z(s) ? e(ue) : Z(o) && e(de, 1);
	}), E(ae);
	var fe = L(ae, 2), pe = I(fe, !0);
	E(fe), E(ie);
	var me = L(ie, 2), he = (e) => {
		$(e, Zr());
	}, ge = (e) => {
		var t = ri(), n = L(I(t), 2), s = I(n), c = L(I(s), 2);
		kr(c), Fe(2), E(s);
		var f = L(s, 2), p = L(I(f), 2);
		kr(p), Fe(2), E(f);
		var m = L(f, 2), _ = I(m);
		xn(() => jr(_, "mappings", (Z(a), Qn(() => JSON.stringify(Z(a)))))), E(m);
		var y = L(m, 2), b = I(y), ie = I(b, !0);
		E(b);
		var ae = L(b, 2), oe = (e) => {
			var t = Qr(), n = I(t, !0);
			E(t), xn((e) => {
				t.disabled = e, mr(n, Z(u) ? "Testing..." : "Test Connection");
			}, [() => (Z(u), Z(r), Qn(() => Z(u) || !Z(r).trim()))]), ar("click", t, v), $(e, t);
		};
		wr(ae, (e) => {
			Z(o) && e(oe);
		});
		var se = L(ae, 2), ce = (e) => {
			var t = $r(), n = I(t, !0);
			E(t), xn(() => {
				t.disabled = Z(g), mr(n, Z(g) ? "Activating..." : "Activate Server");
			}), ar("click", t, ee), $(e, t);
		};
		wr(se, (e) => {
			Z(h) || e(ce);
		});
		var x = L(se, 2), le = (e) => {
			var t = ei();
			ar("click", t, re), $(e, t);
		}, ue = (e) => {
			var t = ti();
			ar("click", t, ne), $(e, t);
		}, de = (e) => {
			var t = ni();
			ar("click", t, ne), $(e, t);
		};
		wr(x, (e) => {
			Z(d) ? e(le) : Z(o) ? e(ue, 1) : e(de, -1);
		}), E(y), E(n), E(t), xn(() => {
			b.disabled = Z(l), mr(ie, Z(l) ? "Saving..." : "Save Settings");
		}), Fr(c, () => Z(r), (e) => F(r, e)), Fr(p, () => Z(i), (e) => F(i, e)), ar("es-path-update", _, (e) => F(a, e.detail)), ar("click", b, te), $(e, t);
	};
	return wr(me, (e) => {
		Z(c) ? e(he) : Z(m) || e(ge, 1);
	}), E(b), xn(() => mr(pe, Z(m) ? "Expand" : "Collapse")), ar("click", fe, () => F(m, !Z(m))), $(e, b), Ue(y);
}
customElements.define("plex-dashboard-card", Kr(oi, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { oi as default };
